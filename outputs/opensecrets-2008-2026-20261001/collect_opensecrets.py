"""Resumable OpenSecrets public-page collector. Python 3.12, requests, bs4.

python collect_opensecrets.py             # resume cached responses
python collect_opensecrets.py --refresh   # fetch a fresh capture
No credentials, CAPTCHA solvers, proxy rotation, or zero-filling of missing data.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, re, sys, time, traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode, urljoin
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
BASE = 'https://www.opensecrets.org'
CYCLES = list(range(2008, 2027, 2))
YEARS = list(range(2008, 2027))
REGISTRY = Path('C:/Users/pgoff/Mentat/mentat/forecast/refit/registry/industries.json')
SCOPES = [
    ('commercial_banks', 'Commercial Banks', 'F03', 'banking', 'OpenSecrets industry; not a Mentat roster aggregate'),
    ('credit_unions', 'Credit Unions', 'F05', 'credit_union', 'OpenSecrets industry; not a Mentat roster aggregate'),
    ('insurance', 'Insurance', 'F09', 'property_casualty_insurance', 'ALL insurance, including life, health, brokers and P&C; not P&C-only'),
    ('auto_manufacturers', 'Auto Manufacturers', 'T2100', '', 'Auto manufacturers category; not all automotive businesses'),
    ('telephone_utilities', 'Telephone Utilities', 'B08', 'telecom', 'Partial telecom scope; do not treat as the complete Mentat telecom roster'),
    ('telecom_services', 'Telecom Services', 'B09', 'telecom', 'Services and equipment; partial telecom scope; kept separate from B08'),
    ('finance_credit_companies', 'Finance / Credit Companies', 'F06', 'credit_arms', 'Broader comparison category, not an exact Mentat credit-arms mapping'),
    ('community_banks', 'Community banks', '', 'community_banks', 'No verified distinct published industry code; requires organisation-level roster aggregation'),
    ('crypto', 'Crypto', '', 'crypto', 'No verified distinct published industry code; requires organisation-level roster aggregation'),
    ('fintech', 'Fintech', '', 'fintech', 'No verified distinct published industry code; requires organisation-level roster aggregation'),
    ('life_insurance', 'Life insurance', '', '', 'No verified distinct published industry page; F09 cannot substitute for life-only'),
]
COMMON = ['source_url','capture_date','capture_utc','as_of_date','as_of_status','source_release_date','source_release_context','raw_file','status','notes']
ID = ['industry','industry_name','opensecrets_code','mentat_key','scope_note']
SCHEMAS = {
 'industry_totals': ID+['cycle','total_usd','individual_usd','pac_usd','soft_outside_usd','democrat_usd','republican_usd','democrat_pct','republican_pct','party_percentage_basis','reconciliation_delta_usd']+COMMON,
 'pac_candidate_giving': ID+['cycle','party','chamber','amount_usd']+COMMON,
 'individual_candidate_giving': ID+['cycle','party','chamber','amount_usd']+COMMON,
 'top_contributors': ID+['cycle','rank','organisation','organisation_name_normalized','total_usd','pac_usd','individual_usd','candidates_parties_usd','democrat_usd','republican_usd','outside_groups_usd','liberal_groups_usd','conservative_groups_usd','pac_individual_split_status','reconciliation_delta_usd','source_reconciliation_status','source_reconciliation_notes']+COMMON,
 'lobbying_annual': ID+['year','total_spend_usd','clients_count','in_house_usd','outside_firm_usd','clients_status','spend_split_status']+COMMON,
 'lobbying_clients': ID+['year','client','spend_usd','in_house_usd','outside_firm_usd','listing_scope']+COMMON,
 'national_election_cost': ['cycle','total_usd','presidential_usd','congressional_usd','dollar_basis','presidential_status','reconciliation_delta_usd']+COMMON,
 'national_candidate_giving': ['cycle','donor_type','party','chamber','amount_usd']+COMMON,
 'candidate_combined_detail': ID+['cycle','chamber','recipient','state','party','combined_pac_individual_usd','recipient_url','chamber_basis']+COMMON,
 'coverage': ID+['table','period','field','reason']+COMMON,
 'industry_mapping': ID+['mapping_status','registry_file']+COMMON,
}

def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def money(value):
    value = str(value).strip().replace(',','').replace('$','').replace('%','').replace('\u2212','-')
    if value in ('', 'N/A', '-', '\u2014'): return None
    if value.startswith('(') and value.endswith(')'): value = '-'+value[1:-1]
    if not re.fullmatch(r'-?\d+(?:\.\d+)?',value): raise ValueError(f'Invalid numeric value: {value!r}')
    n = Decimal(value)
    return int(n) if n == int(n) else float(n)

def rows(table):
    return [[c.get_text(' ',strip=True) for c in tr.select('th,td')] for tr in table.select('tr')]

def ident(scope): return dict(zip(ID,scope))

def normalized(name): return re.sub(r'[^a-z0-9]+',' ',name.casefold()).strip()

# Windows sharing/access errors: 5 access denied, 32 sharing violation, 33 lock violation.
TRANSIENT_WINERRORS = {5, 32, 33}

def replace_with_retry(src, dst, attempts=8, base_delay=0.2, max_delay=2.0, sleep=time.sleep, replace=os.replace):
    """Atomic os.replace, retried a bounded number of times only for transient
    Windows sharing/access failures (e.g. a reader holding the destination open).
    Other errors, and the final failure, propagate unchanged."""
    for attempt in range(1, attempts+1):
        try:
            return replace(src, dst)
        except PermissionError as exc:
            if getattr(exc, 'winerror', None) not in TRANSIENT_WINERRORS or attempt == attempts: raise
            sleep(min(max_delay, base_delay*2**(attempt-1)))

def put_json(path, obj, **retry):
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
    replace_with_retry(tmp,path,**retry)

def put_csv(path, fieldnames, data, **retry):
    tmp = path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w',newline='',encoding='utf-8-sig') as handle:
        writer=csv.DictWriter(handle,fieldnames=fieldnames,extrasaction='raise')
        writer.writeheader()
        writer.writerows(data)
    replace_with_retry(tmp,path,**retry)

def candidate_party(label):
    """Source party code from a recipient label such as 'Name (D-CA)', 'Name (3-UT)'
    or 'Name (R)'. Alphanumeric codes are preserved; '' when the label has none."""
    m = re.search(r'\(([A-Za-z0-9]+)(?:-[A-Za-z]{2})?\)\s*$', label)
    return m[1] if m else ''

def contributor_reconciliation(row):
    """Compare published Grand Total with published Candidates & Parties + Outside
    Spending Groups. Observation only: source values are never adjusted and the
    columns are not assumed to be additive."""
    total, cp, outside = (row.get(k) for k in ('total_usd','candidates_parties_usd','outside_groups_usd'))
    if total is None or cp is None or outside is None:
        return {'reconciliation_delta_usd':None,'source_reconciliation_status':'not_checkable','source_reconciliation_notes':'One or more of Grand Total, Candidates & Parties, Outside Spending Groups not published for this row'}
    delta = total-(cp+outside)
    if delta == 0:
        return {'reconciliation_delta_usd':0,'source_reconciliation_status':'published_columns_consistent','source_reconciliation_notes':''}
    return {'reconciliation_delta_usd':delta,'source_reconciliation_status':'published_columns_not_additive_review','source_reconciliation_notes':f'Published Grand Total minus (Candidates & Parties + Outside Spending Groups) = {delta}; published columns may overlap or be defined differently, so additivity is not assumed. All source values preserved unadjusted; flagged for review.'}

class Collector:
    def __init__(self, refresh=False):
        self.refresh = refresh
        self.session = requests.Session()
        self.session.headers['User-Agent']='MentatResearchCollector/1.0 (public research data; Python requests)'
        self.data = {k:[] for k in SCHEMAS}
        self.seen = {}
        self.requests = 0
        self.started = utc()
        self.last_fetch = 0.0
        self.failed_families = Counter()
        self.events = []
        (ROOT/'raw').mkdir(exist_ok=True)
        (ROOT/'csv').mkdir(exist_ok=True)

    def status(self, phase, current=''):
        put_json(ROOT/'status.json', {'pid':os.getpid(),'started_utc':self.started,'updated_utc':utc(),'phase':phase,'current':current,'http_requests':self.requests,'rows':{k:len(v) for k,v in self.data.items()},'coverage_reasons':dict(Counter(r['reason'] for r in self.data['coverage']))})

    def fetch(self, path, family='public'):
        url = urljoin(BASE,path)
        if url in self.seen: return self.seen[url]
        key = hashlib.sha256(url.encode()).hexdigest()
        meta_file = ROOT/'raw'/f'{key}.json'
        body_file = ROOT/'raw'/f'{key}.html'
        if meta_file.exists() and body_file.exists() and not self.refresh:
            meta = json.loads(meta_file.read_text(encoding='utf-8'))
            html = body_file.read_text(encoding='utf-8')
        elif self.failed_families[family] >= 3:
            meta={'source_url':url,'capture_utc':utc(),'http_status':None,'error':'family_circuit_open_after_three_access_failures','raw_file':''}
            html=''
        else:
            time.sleep(max(0,1.1-(time.monotonic()-self.last_fetch)))
            self.last_fetch=time.monotonic()
            self.status('running',url)
            meta={'source_url':url,'capture_utc':utc(),'raw_file':str(body_file)}
            html=''
            try:
                response = self.session.get(url,timeout=(15,45))
                response.encoding='utf-8'
                html=response.text
                meta.update(http_status=response.status_code,final_url=response.url,content_type=response.headers.get('Content-Type',''))
                if response.status_code in (401,403,429): self.failed_families[family]+=1
                if response.status_code == 429:
                    meta['retry_after']=response.headers.get('Retry-After','')
                    self.failed_families[family]=3
            except requests.RequestException as exc:
                meta.update(http_status=None,error=str(exc))
            self.requests+=1
            body_file.write_text(html,encoding='utf-8')
            meta['sha256']=hashlib.sha256(html.encode()).hexdigest()
            put_json(meta_file,meta)
        soup=BeautifulSoup(html,'html.parser')
        text=soup.get_text(' ',strip=True)
        dates=re.findall(r'(?:data released on|Commission on|data (?:were )?released (?:on )?|data (?:was |were )?(?:updated|retrieved) on)\s*([A-Z][a-z]+ \d{1,2}, \d{4})',text)
        source_date=''
        if dates:
            source_date=datetime.strptime(dates[-1],'%B %d, %Y').date().isoformat()
        meta.update(capture_date=meta['capture_utc'][:10],source_release_date=source_date,source_release_context='FEC page footnote' if source_date and 'Federal Election Commission' in text else '',as_of_date='',as_of_status='not_stated',status='observed' if meta.get('http_status')==200 else 'fetch_failed',notes='')
        if soup.title and ('Just a moment' in soup.title.get_text() or 'Access Denied' in soup.title.get_text()): meta['status']='access_blocked'
        self.events.append({k:meta.get(k,'') for k in ['source_url','capture_utc','http_status','final_url','error','raw_file']})
        self.seen[url]=(soup,meta)
        print(json.dumps({'time':utc(),'url':url,'status':meta['status'],'http':meta.get('http_status')},ensure_ascii=True),flush=True)
        return soup,meta

    def base(self,meta,lobby=False):
        b={k:meta.get(k,'') for k in COMMON}
        if not lobby and b['source_release_date']:
            b.update(as_of_date=b['source_release_date'],as_of_status='page_FEC_release_date_not_necessarily_period_end')
        return b

    def gap(self,scope,table,period,field,reason,meta):
        self.data['coverage'].append({**ident(scope),**self.base(meta), 'table':table,'period':period,'field':field,'reason':reason,'status':'unavailable'})

    def period_ok(self,soup,year):
        sel=soup.select_one('select[name=cycle] option[selected],select[name=select_cycle] option[selected]')
        return bool(sel and sel.get_text(strip=True)==str(year))

    def industry_ok(self,soup,scope):
        title=soup.title.get_text() if soup.title else ''
        return scope[1].casefold() in title.casefold()

    def write(self):
        for name, fields in SCHEMAS.items():
            put_csv(ROOT/'csv'/f'{name}.csv',fields,self.data[name])
        put_json(ROOT/'request_log.json',self.events)
        self.status('running')

    def missing_scope(self,scope,meta):
        for cy in CYCLES:
            b={**ident(scope),**self.base(meta),'cycle':cy,'status':'unmapped_scope','notes':scope[4]}
            self.data['industry_totals'].append(b)
            self.data['top_contributors'].append({**b,'pac_individual_split_status':'unmapped_scope'})
            for table in ['pac_candidate_giving','individual_candidate_giving']:
                for ch in ['House','Senate']:
                    for party in ['D','R']: self.data[table].append({**b,'party':party,'chamber':ch})
            for table in ['industry_totals','top_contributors','pac_candidate_giving','individual_candidate_giving']:
                self.gap(scope,table,cy,'all','unmapped_scope',meta)
        for year in YEARS:
            self.data['lobbying_annual'].append({**ident(scope),**self.base(meta,lobby=True),'year':year,'status':'unmapped_scope','clients_status':'unmapped_scope','spend_split_status':'unmapped_scope','notes':scope[4]})
            self.gap(scope,'lobbying_annual',year,'all','unmapped_scope',meta)

    def industry_totals(self,scope):
        soup,meta=self.fetch('/industries/totals?'+urlencode({'ind':scope[2],'cycle':2026}))
        found={}
        if self.industry_ok(soup,scope):
            for table in soup.select('table'):
                rr=rows(table)
                if not rr or rr[0][:2]!=['Election Cycle','Total Contributions']: continue
                for r in rr[1:]:
                    if len(r)!=9 or not r[0].isdigit() or int(r[0]) not in CYCLES: continue
                    cy=int(r[0]); values=[money(x) for x in r[1:]]
                    row={**ident(scope),**self.base(meta),'cycle':cy,**dict(zip(['total_usd','individual_usd','pac_usd','soft_outside_usd','democrat_usd','republican_usd','democrat_pct','republican_pct'],values)),'party_percentage_basis':'Published percentages: candidates and parties only; outside spending excluded','reconciliation_delta_usd':values[0]-sum(values[1:4])}
                    if row['reconciliation_delta_usd']!=0: row.update(status='source_reconciliation_difference',notes='Published total differs from the sum of published donor-type columns; additivity not assumed. Preserved without adjustment; review.')
                    found[cy]=row
        for cy in CYCLES:
            if cy in found: self.data['industry_totals'].append(found[cy])
            else:
                self.data['industry_totals'].append({**ident(scope),**self.base(meta),'cycle':cy,'as_of_date':'','as_of_status':'unavailable','status':'cycle_not_published','notes':'No row for requested cycle in published totals table'})
                self.gap(scope,'industry_totals',cy,'all','cycle_not_published',meta)

    def contributors(self,scope,cy):
        soup,meta=self.fetch('/industries/contrib?'+urlencode({'ind':scope[2],'cycle':cy}))
        count=0
        missing_split=False
        if self.period_ok(soup,cy) and self.industry_ok(soup,scope):
            for table in soup.select('table'):
                rr=rows(table)
                if not rr or rr[0][:2]!=['Rank','Contributor']: continue
                hdr=rr[0]
                for r in rr[1:]:
                    if len(r)!=len(hdr) or not r[0].isdigit(): continue
                    d=dict(zip(hdr,r))
                    row={**ident(scope),**self.base(meta),'cycle':cy,'rank':int(r[0]),'organisation':r[1],'organisation_name_normalized':normalized(r[1]),'pac_individual_split_status':'not_published_on_contributor_page','status':'partial','notes':'Published top-contributor list, not all organisations. Individual attribution includes employees, owners, members and immediate families; not employee-only. No roster equivalence implied.'}
                    for src,dst in [('Grand Total','total_usd'),('Total','total_usd'),('Total to Candidates & Parties','candidates_parties_usd'),('Dems','democrat_usd'),('Repubs','republican_usd'),('Total to Outside Spending Groups','outside_groups_usd'),('Liberal Groups','liberal_groups_usd'),('Conservative Groups','conservative_groups_usd'),('PACs','pac_usd'),('Individuals','individual_usd')]:
                        if src in d: row[dst]=money(d[src])
                    if 'pac_usd' in row and 'individual_usd' in row: row.update(status='observed',pac_individual_split_status='observed')
                    else: missing_split=True
                    row.update(contributor_reconciliation(row))
                    self.data['top_contributors'].append(row); count+=1
        if not count:
            self.data['top_contributors'].append({**ident(scope),**self.base(meta),'cycle':cy,'status':'unavailable','as_of_date':'','as_of_status':'unavailable','notes':'Requested cycle or contributor table unavailable'})
            self.gap(scope,'top_contributors',cy,'all','requested_cycle_or_table_unavailable',meta)
        elif missing_split: self.gap(scope,'top_contributors',cy,'pac_usd;individual_usd','donor_type_split_not_published_on_page',meta)

    def candidates(self,scope,cy):
        for ch in ['House','Senate']:
            soup,meta=self.fetch('/industries/summary?'+urlencode({'ind':scope[2],'cycle':cy,'recipdetail':ch[0],'mem':'N'}))
            valid=self.period_ok(soup,cy) and self.industry_ok(soup,scope)
            if valid:
                for table in soup.select('table'):
                    rr=rows(table)
                    if not rr or rr[0][-2:]!=['State','Amount']: continue
                    for tr in table.select('tr')[1:]:
                        r=[c.get_text(' ',strip=True) for c in tr.select('th,td')]
                        if len(r)!=3: continue
                        a=tr.select_one('a[href]')
                        self.data['candidate_combined_detail'].append({**ident(scope),**self.base(meta),'cycle':cy,'chamber':ch,'recipient':r[0],'state':r[1],'party':candidate_party(r[0]), 'combined_pac_individual_usd':money(r[2]),'recipient_url':urljoin(BASE,a['href']) if a else '', 'chamber_basis':'OpenSecrets candidate-list classification; not independently office-verified','notes':'Combined PAC and individual dollars. May include presidential overlap or office changes; not used as a donor-type subtotal.'})
            reason='donor_type_split_not_published_on_page' if valid else 'requested_cycle_or_table_unavailable'
            for table in ['pac_candidate_giving','individual_candidate_giving']:
                for party in ['D','R']:
                    self.data[table].append({**ident(scope),**self.base(meta),'cycle':cy,'chamber':ch,'party':party,'status':'unavailable','as_of_date':meta.get('source_release_date','') if valid else '', 'as_of_status':'page_FEC_release_date' if valid and meta.get('source_release_date') else 'unavailable','notes':reason})
                self.gap(scope,table,cy,'amount_usd:'+ch,reason,meta)

    def lobbying(self,scope):
        soup,meta=self.fetch('/industries/lobbying?'+urlencode({'ind':scope[2],'cycle':2024}))
        annual={}
        if self.industry_ok(soup,scope):
            for el in soup.select('[data-source]'):
                try: data=json.loads(el['data-source'])
                except json.JSONDecodeError: continue
                for point in data.get('data',[]):
                    match=re.fullmatch(r"'(\d{2})",point.get('label',''))
                    if not match: continue
                    yy=int(match[1]); year=1900+yy if yy>=90 else 2000+yy
                    if year in YEARS: annual[year]={**ident(scope),**self.base(meta,lobby=True),'year':year,'total_spend_usd':money(point['value']),'status':'partial','clients_status':'unavailable','spend_split_status':'not_published_on_industry_page','notes':'Annual chart data embedded in page, by explicit year label. FEC footnote does not establish a lobbying as-of date.'}
        for year in YEARS:
            s,m=self.fetch('/industries/lobbying?'+urlencode({'ind':scope[2],'cycle':year}))
            row=annual.get(year,{**ident(scope),**self.base(m,lobby=True),'year':year,'status':'unavailable','clients_status':'unavailable','spend_split_status':'unavailable'})
            text=s.get_text(' ',strip=True)
            valid=self.industry_ok(s,scope) and bool(re.search(r'Top Lobbying Clients,\s*'+str(year)+r'\b',text))
            if valid:
                count=re.search(r'([\d,]+)\s+Number of Clients',text)
                if count: row.update(clients_count=money(count[1]),clients_status='observed',**{k:v for k,v in self.base(m,lobby=True).items() if k not in ['status','notes']})
                for table in s.select('table'):
                    rr=rows(table)
                    if not rr or rr[0]!=['Client/Parent Organization','Total']: continue
                    for r in rr[1:]:
                        if len(r)!=2 or not re.match(r'^-?\$',r[1]): continue
                        self.data['lobbying_clients'].append({**ident(scope),**self.base(m,lobby=True),'year':year,'client':r[0],'spend_usd':money(r[1]),'listing_scope':'Published top clients / parent organisations; may not equal client count','status':'partial','notes':'In-house/outside-firm split unavailable. Client totals may include outside-firm fees; do not add fees again.'})
            else: self.gap(scope,'lobbying_clients',year,'all','year_not_published_on_accessible_client_page',m)
            if row.get('clients_count') is None: self.gap(scope,'lobbying_annual',year,'clients_count','year_not_published_on_accessible_client_page',m)
            self.gap(scope,'lobbying_annual',year,'in_house_usd;outside_firm_usd','requires_lobbying_detail_or_bulk_data',m)
            if year==2026: self.gap(scope,'lobbying_annual',year,'as_of_date','lobbying_source_as_of_not_stated',m)
            self.data['lobbying_annual'].append(row)
        self.write()

    def national(self):
        scope=('national','National','','','All industries; candidates only')
        soup,meta=self.fetch('/elections-overview/cost-of-election?infl=N')
        inflation=soup.select_one('input[name=infl]')
        nominal=bool(inflation and inflation.get('value')=='N' and not inflation.has_attr('checked'))
        found={}
        for table in soup.select('table') if nominal else []:
            rr=rows(table)
            if not rr or rr[0]!=['Cycle','Total Cost of Election','Congressional Races','Presidential Race']: continue
            for r in rr[1:]:
                if len(r)!=4: continue
                c=re.fullmatch(r'(\d{4})\*?',r[0])
                if not c or int(c[1]) not in CYCLES: continue
                cy=int(c[1]); total,congress,president=map(money,r[1:])
                delta=total-congress-(president or 0)
                found[cy]={**self.base(meta),'cycle':cy,'total_usd':total,'congressional_usd':congress,'presidential_usd':president,'dollar_basis':'nominal USD; infl=N','presidential_status':'not_applicable_midterm' if president is None else 'observed','reconciliation_delta_usd':delta,'status':'observed' if delta==0 else 'source_reconciliation_difference','notes':'Source election-cost estimates; includes candidates, parties and outside groups. Published rounding differences preserved.'}
        for cy in CYCLES:
            if cy in found: self.data['national_election_cost'].append(found[cy])
            else:
                self.data['national_election_cost'].append({**self.base(meta),'cycle':cy,'dollar_basis':'nominal USD','status':'cycle_not_published','as_of_date':'','as_of_status':'unavailable'})
                self.gap(scope,'national_election_cost',cy,'all','cycle_not_published',meta)
            _,m=self.fetch('/elections-overview/where-the-money-came-from?'+urlencode({'cycle':cy}))
            # This page reports rounded percentages for members running for election,
            # not dollar totals for the complete candidate universe. Never multiply
            # these percentages by a different fundraising total.
            for typ in ['PAC','individual']:
                for party in ['D','R']:
                    self.data['national_candidate_giving'].append({**self.base(m),'cycle':cy,'donor_type':typ,'party':party,'chamber':'All federal candidates','status':'unavailable','as_of_date':'','as_of_status':'unavailable','notes':'Accessible comparison reports rounded member-only percentages, not requested all-candidate nominal dollar totals; requires detail/bulk data'})
            self.gap(scope,'national_candidate_giving',cy,'amount_usd','all_candidate_dollar_totals_not_exposed_on_comparison_page',m)
        self.write()

    def run(self):
        taxonomy,tmeta=self.fetch('/industries/slist')
        published={a['href'].split('ind=')[-1]:a.get_text(' ',strip=True) for a in taxonomy.select('a[href]') if '/industries/indus?ind=' in a['href']}
        put_json(ROOT/'source_taxonomy.json',{'source_url':tmeta['source_url'],'capture_utc':tmeta['capture_utc'],'industries':published})
        if REGISTRY.exists():
            content=REGISTRY.read_bytes()
            (ROOT/'mentat_industry_registry_snapshot.json').write_bytes(content)
            put_json(ROOT/'registry_provenance.json',{'path':str(REGISTRY),'sha256':hashlib.sha256(content).hexdigest(),'capture_utc':utc()})
        for scope in SCOPES:
            self.data['industry_mapping'].append({**ident(scope),**self.base(tmeta),'mapping_status':'published_comparison_scope' if scope[2] in published else 'unmapped','registry_file':str(REGISTRY),'notes':scope[4]})
            if not scope[2]: self.missing_scope(scope,tmeta)
        self.write()
        self.national()
        # Audit protected families with a small bounded sample, not repeated bypass attempts.
        for path,family in [('/political-action-committees-pacs','pac_detail'),('/political-action-committees-pacs/industry-detail/F03/2024','pac_detail'),('/federal-lobbying/industries/summary?id=F03&year=2026','lobbying_detail'),('/bulk-data','bulk')]:
            s,m=self.fetch(path,family)
            if m['status']!='observed': self.gap(('national','National','','',''),'access',2026,family,m['status'],m)
        for scope in SCOPES:
            if not scope[2]: continue
            if scope[2] not in published:
                self.missing_scope(scope,tmeta)
                continue
            self.industry_totals(scope)
            self.write()
            self.lobbying(scope)
            for cy in reversed(CYCLES):
                self.contributors(scope,cy)
                self.candidates(scope,cy)
                self.write()
        self.write()
        self.validate()
        self.status('finished_with_gaps')

    def validate(self):
        tests={}
        for table in ['industry_totals','pac_candidate_giving','individual_candidate_giving','lobbying_annual']:
            period='year' if table=='lobbying_annual' else 'cycle'
            cols=['industry',period]+(['party','chamber'] if 'candidate_giving' in table else [])
            keys=[tuple(r.get(c) for c in cols) for r in self.data[table]]
            tests[table+'_unique_keys']=len(keys)==len(set(keys))
        tests['provenance_on_all_rows']=all(r.get('source_url') and r.get('capture_date') for table in self.data.values() for r in table)
        tests['no_fabricated_split_values']=all(r.get('amount_usd') is None for t in ['pac_candidate_giving','individual_candidate_giving','national_candidate_giving'] for r in self.data[t] if r['status']=='unavailable')
        tests['cycle_range']=all(r['cycle'] in CYCLES for table in self.data.values() for r in table if 'cycle' in r)
        put_json(ROOT/'validation.json',{'checked_utc':utc(),'tests':tests,'passed':all(tests.values()),'source_reconciliation_differences':sum(r.get('status')=='source_reconciliation_difference' for table in self.data.values() for r in table)})
        if not all(tests.values()): raise ValueError('CSV validation failed; see validation.json')

if __name__=='__main__':
    args=argparse.ArgumentParser()
    args.add_argument('--refresh',action='store_true')
    options=args.parse_args()
    collector=Collector(options.refresh)
    put_json(ROOT/'process.json',{'pid':os.getpid(),'executable':sys.executable,'script':str(Path(__file__).resolve()),'started_utc':utc(),'command':sys.argv})
    try:
        collector.run()
    except BaseException as exc:
        try: collector.write()
        except Exception as write_exc: print(f'final write failed: {write_exc!r}',file=sys.stderr,flush=True)
        collector.status('failed',str(exc))
        traceback.print_exc()
        raise
