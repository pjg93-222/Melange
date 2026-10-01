"""Issue an immutable, genuinely prospective control forecast; score only after maturity."""
import argparse
import collections
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import joblib
import numpy as np
import pandas as pd
import requests
from threadpoolctl import threadpool_limits

from common import CODE, OLD, OUT, digest, log, read_json, stamp, write_json
from audit_data import parse_bill
from build_panel import (FEATURES, TOPIC_NAMES, get_bills, get_members, get_ideology,
                          prior_stats, term_at, ordinal, topic_for)
from extend_public import Timeline
from run_models import predict, calibrate

SNAPSHOT=OUT/'prospective_20260905'
CONTROL_MODELS=['logistic_history','logistic_dynamic','time_to_sign','boosted_dynamic','boosted_public_coverage']


def sources(directory=SNAPSHOT):
    directory=Path(directory)
    directory.mkdir(exist_ok=True)
    path=directory/'source_receipt.json'
    if path.exists():return read_json(path)
    urls={
      'billstatus_hr.zip':'https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119-hr.zip',
      'billstatus_s.zip':'https://www.govinfo.gov/bulkdata/BILLSTATUS/119/s/BILLSTATUS-119-s.zip',
      'house_members.xml':'https://clerk.house.gov/xml/lists/MemberData.xml',
      'senate_members.xml':'https://www.senate.gov/general/contact_information/senators_cfm.xml'}
    def fetch(item):
        name,url=item;dest=directory/name
        started=stamp()
        response=requests.get(url,timeout=(15,90),stream=True);response.raise_for_status()
        with dest.open('wb') as f:
            for block in response.iter_content(1024*1024):f.write(block)
        if name.endswith('.zip'):
            with zipfile.ZipFile(dest) as z:
                if z.testzip() is not None:raise RuntimeError('Corrupt bill snapshot')
        else:ET.parse(dest)
        return name,dict(url=url,path=str(dest),sha256=digest(dest),observed_started_utc=started,
                         observed_completed_utc=stamp(),last_modified=response.headers.get('Last-Modified'))
    with ThreadPoolExecutor(max_workers=2) as pool:receipts=dict(pool.map(fetch,urls.items()))
    result=dict(captured_utc=stamp(),sources=receipts)
    write_json(path,result);log('Prospective official sources captured')
    return result


def serving_roster(directory=SNAPSHOT):
    roster={}
    house=ET.parse(directory/'house_members.xml').getroot()
    for row in house.findall('members/member'):
        r=row.find('member-info');mid=r.findtext('bioguideID')
        if not mid or r.findtext('lastname','').lower()=='vacant':continue
        state=r.find('state').attrib['postal-code'];sd=row.findtext('statedistrict')
        roster[mid]=dict(chamber='House',state=state,party={'D':'Democrat','R':'Republican'}.get(r.findtext('party'),'Independent'),
                         name=r.findtext('official-name'),district=int(sd[2:]))
    senate=ET.parse(directory/'senate_members.xml').getroot()
    for r in senate.findall('member'):
        mid=r.findtext('bioguide_id')
        if mid:roster[mid]=dict(chamber='Senate',state=r.findtext('state'),party={'D':'Democrat','R':'Republican'}.get(r.findtext('party'),'Independent'),
                               name=r.findtext('first_name')+' '+r.findtext('last_name'),district=None)
    if not (400<=sum(v['chamber']=='House' for v in roster.values())<=450 and 95<=sum(v['chamber']=='Senate' for v in roster.values())<=100):
        raise RuntimeError('Unexpected serving-roster counts')
    return roster


def current_bills():
    rows=[]
    for filename in ['billstatus_hr.zip','billstatus_s.zip']:
        with zipfile.ZipFile(SNAPSHOT/filename) as z:
            for name in z.namelist():
                if not name.endswith('.xml'):continue
                b=parse_bill(z.read(name))
                if b['congress']!=119:raise ValueError('Wrong Congress snapshot')
                b['intro']=ordinal(b['introduced']);b['title_text']=' '.join(t['text'] for t in b['titles'])
                b['topic']=topic_for(b['title_text']);b['joins']={c['member']:ordinal(c['date']) for c in b['cosponsors']}
                b['enacted']=min([ordinal(a['date']) for a in b['actions'] if a['date'] and a['type'].lower()=='president' and
                    ('became' in a['text'].lower() and 'law' in a['text'].lower() or 'signed by president' in a['text'].lower())] or [10**9])
                rows.append(b)
    return rows


def make_public(mids):
    index={mid:i for i,mid in enumerate(mids)};all_records=[];topics=collections.defaultdict(list);bills=collections.defaultdict(list)
    for line in (OLD/'public_evidence_extended.jsonl').open(encoding='utf-8'):
        r=json.loads(line)
        if r['member'] not in index:continue
        code=index[r['member']];all_records.append((code,r['day'],0,0))
        for topic in r['topics']:topics[topic].append((code,r['day'],topic in r['positive_topics'],topic in r['negative_topics']))
        for bill in r['bills']:bills[bill].append((code,r['day'],bill in r['positive_bills'],bill in r['negative_bills']))
    return Timeline(all_records),{k:Timeline(v) for k,v in topics.items()},{k:Timeline(v) for k,v in bills.items()},Timeline([])


def issue():
    if (SNAPSHOT/'forecast_manifest.json').exists():raise RuntimeError('Forecast already issued; never overwrite')
    receipt=sources();today=dt.datetime.now(dt.timezone.utc).date();day=today.toordinal()
    if today.isoformat()!='2026-09-05':raise RuntimeError('This snapshot is explicitly dated 2026-09-05; use a new snapshot directory for a later run')
    history=get_bills();bykey={b['key']:b for b in history};members,_=get_members();roster=serving_roster()
    mids=sorted(set(roster)&set(members));midcodes={mid:i for i,mid in enumerate(mids)}
    ideology=get_ideology();pri=prior_stats(history,118);analogues=read_json(OLD/'analogue_links.json')
    public,topics,bill_timeline,empty=make_public(mids)
    bills=current_bills();rows=[];vectors=[];qualified=[];counts=collections.Counter()
    for b in sorted(bills,key=lambda b:b['key']):
        age=day-b['intro']
        if not b['finance_at_introduction'] or not 0<=age<=175 or b['enacted']<=day:continue
        sponsor=members.get(b['sponsor'])
        if not sponsor:counts['missing_sponsor_history_bills']+=1;continue
        st=roster.get(b['sponsor']) or term_at(sponsor,b['intro'],b['chamber'])
        if not st:continue
        an=analogues.get(b['key']);prior_bill=bykey[an['prior_key']] if an else None
        joined={mid:d for mid,d in b['joins'].items() if d<day};join_dates=list(joined.values())
        actions=[a for a in b['actions'] if a['date'] and ordinal(a['date'])<day];action_days=[ordinal(a['date']) for a in actions]
        joined_parties=collections.Counter(roster[jm]['party'] for jm in joined if jm in roster)
        group=len(qualified);qualified.append(b['key'])
        eligible=[mid for mid in mids if roster[mid]['chamber']==b['chamber'] and mid!=b['sponsor'] and b['joins'].get(mid,10**9)>day]
        codes=np.array([midcodes[mid] for mid in eligible]);t=topics.get(b['topic'],empty);bt=bill_timeline.get(b['key'],empty)
        public_block=np.column_stack([public.query(codes,day)[:,0],t.query(codes,day),bt.query(codes,day),bt.query(codes,day,30)[:,0],t.query(codes,day,30)[:,0]])
        for j,mid in enumerate(eligible):
            person=members[mid];term=roster[mid];mi=ideology.get((118,mid));si=ideology.get((118,b['sponsor']))
            miv=mi or (0,0);siv=si or (0,0);affinity=pri['affinity'][(mid,b['sponsor'])]
            propensity=pri['counts'][mid]/max(1,pri['chamber_totals'][b['chamber']]);tc=pri['topic_counts'][(mid,b['topic'])];nt=pri['topic_totals'][(b['chamber'],b['topic'])]
            value=[np.log1p(pri['counts'][mid]),propensity,np.log1p(affinity),(affinity+.3)/(pri['sponsor_totals'][b['sponsor']]+10),np.log1p(len(pri['neighbors'][mid])),
                   *miv,*siv,abs(miv[0]-siv[0]) if mi and si else 0,abs(miv[1]-siv[1]) if mi and si else 0,
                   int(mi is None),int(si is None),int(term['party']==st['party']),int(term['state']==st['state']),int(b['chamber']=='Senate'),
                   (day-person['first_start'])/365.25,int(st['party']=='Republican'),
                   len({c['code'] for c in b['committees'] if c['date']==b['introduced'] and c['activity'].lower()=='referred to'})]
            value += [int(b['topic']==topic) for topic in TOPIC_NAMES]
            value += [np.log1p(tc),(tc+10*propensity)/(nt+10),tc/max(1,pri['counts'][mid]),an['similarity'] if an else 0,int(an is not None),
                      int(prior_bill is not None and mid in prior_bill['joins']),int(prior_bill is not None and mid==prior_bill['sponsor'])]
            value += [np.log1p(age),age,np.log1p(len(joined)),np.log1p(sum(day-7<=d<day for d in join_dates)),np.log1p(sum(day-30<=d<day for d in join_dates)),
                      joined_parties[term['party']]/max(1,len(joined)),len(pri['neighbors'][mid]&joined.keys())/max(1,len(joined)),
                      min(365,day-max(join_dates)) if join_dates else 365,np.log1p(sum(d>=day-30 for d in action_days)),np.log1p(len(action_days)),
                      min(365,day-max(action_days)) if action_days else 365,int(any(a['type'].lower()=='passage' for a in actions)),day-dt.date(2025,1,3).toordinal()]
            value+=np.log1p(public_block[j]).tolist()
            if len(value)!=len(FEATURES):raise ValueError('Feature alignment mismatch')
            vectors.append(value);rows.append(dict(bill=b['key'],member=mid,member_name=term['name'],chamber=b['chamber'],group=group,
                 forecast_date=today.isoformat(),bill_age=age,topic=b['topic'],state=term['state'],party=term['party'],district=term['district']))
    x=np.asarray(vectors,dtype=np.float32);del vectors
    if not np.isfinite(x).all():raise ValueError('Nonfinite live features')
    np.save(SNAPSHOT/'features.npy',x)
    frame=pd.DataFrame(rows);model_hashes={}
    for name in CONTROL_MODELS:
        path=OLD/'models'/f'final_{name}.joblib';artifact=joblib.load(path);model_hashes[name]=digest(path)
        frame[name]=calibrate(predict(artifact,x),artifact['calibration'])
        frame[name+'_rank']=frame.groupby('bill')[name].rank(method='first',ascending=False).astype(int)
    frame.to_parquet(SNAPSHOT/'forecasts.parquet',index=False)
    frame[frame.boosted_public_coverage_rank<=8].sort_values('boosted_public_coverage',ascending=False).to_csv(SNAPSHOT/'top_eight_forecasts.csv',index=False)
    write_json(SNAPSHOT/'forecast_manifest.json',dict(issued_utc=stamp(),forecast_date=today.isoformat(),
        outcome_start=(today+dt.timedelta(days=1)).isoformat(),outcome_end=(today+dt.timedelta(days=30)).isoformat(),
        earliest_scoring_date=(today+dt.timedelta(days=31)).isoformat(),status='PENDING_OUTCOMES',rows=len(frame),bills=frame.bill.nunique(),
        members=frame.member.nunique(),models=CONTROL_MODELS,model_sha256=model_hashes,source_receipt_sha256=digest(SNAPSHOT/'source_receipt.json'),
        features_sha256=digest(SNAPSHOT/'features.npy'),forecasts_sha256=digest(SNAPSHOT/'forecasts.parquet'),code_sha256=digest(__file__),
        feature_names=FEATURES,public_evidence_sha256=digest(OLD/'public_evidence_extended.jsonl'),
        member_coverage=dict(official_roster=len(roster),historical_identity_matched=len(mids),unmatched=sorted(set(roster)-set(members))),
        note='Official sources observed now. Features use dates strictly before forecast day; candidates exclude currently reported prior/same-day signers. No future success rate is available. Historical title links and public-source corpus retained from phase one.'))
    log(f'PROSPECTIVE FORECAST ISSUED: {len(frame):,} rows, {frame.bill.nunique()} bills; outcomes pending through {today+dt.timedelta(days=30)}')


def apply_outcomes(frame, joins, manifest, later_members, service_review):
    """Keep issued ranks; disclose reporting corrections and full-window censoring."""
    if not service_review.get('complete_departure_review') or service_review.get('reviewed_through','')<manifest['outcome_end']:
        raise ValueError('A complete, source-backed serving-member review through outcome end is required')
    if not service_review.get('sources'):
        raise ValueError('Serving-member review must cite dated official sources')
    departures=service_review.get('last_serving_dates',{})
    missing=set(frame.member)-set(later_members)-set(departures)
    if missing:raise ValueError(f'Unresolved serving-member departures: {sorted(missing)}')
    for mid,day in departures.items():dt.date.fromisoformat(day)
    event=[];correction=[];censored=[]
    for bill,mid in frame[['bill','member']].itertuples(index=False,name=None):
        if bill not in joins:raise ValueError('Frozen bill missing from later snapshot')
        day=joins[bill].get(mid)
        correction.append(bool(day and day<=manifest['forecast_date']))
        event.append(bool(day and manifest['outcome_start']<=day<=manifest['outcome_end']))
        censored.append(mid in departures and departures[mid]<manifest['outcome_end'])
    frame=frame.copy()
    frame['event']=event;frame['late_reported_prior_signature']=correction;frame['service_censored']=censored
    return frame


def score(later_snapshot, service_review_path):
    manifest=read_json(SNAPSHOT/'forecast_manifest.json')
    if dt.datetime.now(dt.timezone.utc).date()<dt.date.fromisoformat(manifest['earliest_scoring_date']):
        raise RuntimeError(f"Outcomes are pending. Earliest scoring date: {manifest['earliest_scoring_date']}")
    if digest(SNAPSHOT/'forecasts.parquet')!=manifest['forecasts_sha256']:raise RuntimeError('Frozen forecasts changed')
    if not later_snapshot:raise ValueError('Provide a separately captured, complete later BILLSTATUS snapshot receipt')
    if not service_review_path:raise ValueError('Provide --service-review with a source-backed complete departure review')
    later=Path(later_snapshot);r=read_json(later/'source_receipt.json')
    if dt.datetime.fromisoformat(r['captured_utc']).date()<dt.date.fromisoformat(manifest['earliest_scoring_date']):raise ValueError('Later roster is not mature')
    for name,source in r['sources'].items():
        if digest(later/name)!=source['sha256']:raise ValueError('Later snapshot hash mismatch')
    later_members=serving_roster(later)
    joins={}
    for name in ['billstatus_hr.zip','billstatus_s.zip']:
        if digest(later/name)!=r['sources'][name]['sha256']:raise ValueError('Later snapshot hash mismatch')
        with zipfile.ZipFile(later/name) as z:
            for key in z.namelist():
                if key.endswith('.xml'):
                    b=parse_bill(z.read(key));dates={}
                    for c in b['cosponsors']:
                        dates[c['member']]=min(c['date'],dates.get(c['member'],c['date']))
                    joins[b['key']]=dates
    frame=pd.read_parquet(SNAPSHOT/'forecasts.parquet')
    models=list(CONTROL_MODELS)
    addon_path=SNAPSHOT/'network_forecast_manifest.json'
    if addon_path.exists():
        addon=read_json(addon_path)
        if digest(SNAPSHOT/'forecast_manifest.json')!=addon['original_forecast_manifest_sha256']:
            raise ValueError('Network forecast is linked to a different control snapshot')
        if dt.datetime.fromisoformat(addon['issued_utc']).date().isoformat()!=manifest['forecast_date']:
            raise ValueError('Network challenger was issued on a different date')
        if digest(SNAPSHOT/'network_forecasts.parquet')!=addon['forecasts_sha256']:
            raise ValueError('Network predictions changed')
        network=pd.read_parquet(SNAPSHOT/'network_forecasts.parquet')
        if not network[['bill','member']].equals(frame[['bill','member']]):
            raise ValueError('Network and control candidate rows differ')
        name=addon['model_name'];models.append(name)
        frame[name]=network[name];frame[name+'_rank']=network[name+'_rank']
    frame=apply_outcomes(frame,joins,manifest,later_members,read_json(service_review_path))
    # Eligibility corrections are disclosed; do not count old backfilled signatures as forecasts won.
    scored=frame[~frame.late_reported_prior_signature & ~frame.service_censored]
    metrics_out={}
    for name in models:
        picks=scored[scored[name+'_rank']<=8]
        metrics_out[name]=dict(recommendations=len(picks),hits=int(picks.event.sum()),precision=float(picks.event.mean()))
    paired={};selective={}
    if 'boosted_network_refit' in models:
        codes,bills=pd.factorize(scored.bill);n=len(bills)
        weights=np.random.default_rng(1016).multinomial(n,np.full(n,1/n),size=3000)
        vectors={}
        for name in ['boosted_public_coverage','boosted_network_refit']:
            picked=(scored[name+'_rank']<=8).to_numpy()
            hits=np.bincount(codes[picked],weights=scored.event.to_numpy()[picked],minlength=n)
            slots=np.bincount(codes[picked],minlength=n)
            denominator=weights@slots
            vectors[name]=np.divide(weights@hits,denominator,out=np.full(len(weights),np.nan),where=denominator>0)
        delta=vectors['boosted_network_refit']-vectors['boosted_public_coverage']
        paired=dict(primary_comparison='boosted_network_refit minus boosted_public_coverage',
            delta_precision=metrics_out['boosted_network_refit']['precision']-metrics_out['boosted_public_coverage']['precision'],
            whole_bill_bootstrap_ci95=np.nanquantile(delta,[.025,.975]).tolist(),replicates=3000)
    policy_path=SNAPSHOT/'shortlist_policy.json'
    if policy_path.exists():
        policy=read_json(policy_path)
        if dt.datetime.fromisoformat(policy['issued_utc']).date().isoformat()!=manifest['forecast_date']:
            raise ValueError('Shortlist policy was not frozen on forecast day')
        if policy['control_prediction_sha256']!=manifest['forecasts_sha256']:
            raise ValueError('Shortlist policy references different forecasts')
        if digest(SNAPSHOT/'network_forecasts.parquet')!=policy['network_prediction_sha256']:
            raise ValueError('Shortlist policy network predictions changed')
        for name,rules in policy['policies'].items():
            selective[name]=[]
            for rule in rules:
                picked=scored[(scored[name+'_rank']<=8)&(scored[name]>=rule['cutoff'])]
                selective[name].append(dict(**rule,scored_recommendations=len(picked),hits=int(picked.event.sum()),
                    precision=float(picked.event.mean()) if len(picked) else None))
    path=SNAPSHOT/'prospective_results.json'
    if path.exists():raise RuntimeError('Prospective result already saved; use a separately versioned correction')
    write_json(path,dict(scored_utc=stamp(),metrics=metrics_out,late_reported_prior_signatures=int(frame.late_reported_prior_signature.sum()),
                          paired_primary_comparison=paired,selective_policies=selective,
                          service_censored_rows=int(frame.service_censored.sum()),service_review_sha256=digest(service_review_path),
                          later_source_receipt_sha256=digest(later/'source_receipt.json'),
                          note='Original issued ranks retained, with no replacement recommendations after reporting corrections or service censoring.'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['capture','issue','score']);parser.add_argument('--later-snapshot')
    parser.add_argument('--output-dir');parser.add_argument('--service-review')
    args=parser.parse_args()
    with threadpool_limits(limits=2):
        sources(args.output_dir or SNAPSHOT) if args.phase=='capture' else issue() if args.phase=='issue' else score(args.later_snapshot,args.service_review)
