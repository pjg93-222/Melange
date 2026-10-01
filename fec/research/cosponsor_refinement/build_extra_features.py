"""Align text and demographic additions to the original immutable risk rows."""
import collections
import datetime as dt

import numpy as np
import pandas as pd
import yaml

from common import OLD, OUT, ROOT, digest, log, read_json, stamp, write_json
from build_panel import FEATURES, ordinal

TEXT=['text_pair_available','text_body_dice','text_body_length_ratio','text_body_exact','text_body_close',
      'text_prior_support','text_prior_sponsor']
DEMOGRAPHIC=[prefix+name for prefix in ['state_','district_'] for name in
             ['log_population','median_age','log_income','poverty_rate','renter_rate','acs_missing']]
FIPS=dict(zip('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR'.split(),
              '01 02 04 05 06 08 09 10 11 12 13 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 44 45 46 47 48 49 50 51 53 54 55 56 72'.split()))
RELEASE_2022=dt.date(2023,10,1).toordinal()


def demographic_vector(record):
    if record is None:return [0,0,0,0,0,1]
    v=record['values']
    needed=['population','median_age','median_household_income','below_poverty','poverty_universe','renter_housing','occupied_housing']
    if any(v.get(k) is None for k in needed) or not v['poverty_universe'] or not v['occupied_housing']:
        return [0,0,0,0,0,1]
    return [np.log1p(v['population']),v['median_age'],np.log1p(v['median_household_income']),
            v['below_poverty']/v['poverty_universe'],v['renter_housing']/v['occupied_housing'],0]


def demographic_lookup(data,cg,day,state,district,is_senate):
    state_code=FIPS.get(state)
    sy=2019 if cg==117 else 2022 if day>=RELEASE_2022 else 2021
    sv=data.get((sy,'04000US'+str(state_code))) if state_code else None
    dv=None
    if not is_senate and state_code and district is not None:
        valid=(cg==117 and state!='NC') or (cg==118 and day>=RELEASE_2022)
        if valid:
            dy=2019 if cg==117 else 2022
            dv=data.get((dy,f'50000US{state_code}{int(district):02d}'))
    return demographic_vector(sv)+demographic_vector(dv)


def build():
    if (OUT/'extra_feature_receipt.json').exists():raise RuntimeError('Extra features already frozen')
    pairs={r['key']:r for r in read_json(OUT/'predecessor_pairs_v2.json')}
    demo={(r['year'],r['geoid']):r for r in read_json(OUT/'historical_demographics_v2.json')}
    identifiers=read_json(OLD/'identifiers.json');keys=identifiers['bills'];mids=identifiers['members']
    folder=ROOT/'data/staffer_network/reference/congress-legislators/750c0608efb6ef1fc3257ba72c99af3771d35088'
    terms={}
    for filename in ['legislators-current.yaml','legislators-historical.yaml']:
        for person in yaml.load((folder/filename).read_bytes(),Loader=yaml.CSafeLoader):
            mid=person['id'].get('bioguide')
            if mid not in mids:continue
            terms[mid]=[{**t,'lo':ordinal(t['start']),'hi':ordinal(t['end'])} for t in person['terms'] if t['type'] in ['rep','sen']]
    splits={}
    for cg in [117,118]:
        m=pd.read_parquet(OLD/f'meta_{cg}.parquet')
        x=np.memmap(OLD/f'X_{cg}.f32',mode='r',dtype=np.float32,shape=(len(m),len(FEATURES)))
        path=OUT/f'extra_{cg}.f32';extra=np.memmap(path,mode='w+',dtype=np.float32,shape=(len(m),len(TEXT+DEMOGRAPHIC)))
        table=np.zeros((len(keys),5),dtype=np.float32)
        for i,key in enumerate(keys):
            p=pairs.get(key,{})
            table[i]=[p.get('available',False),p.get('dice',0),p.get('length_ratio',0),p.get('exact',False),p.get('close',False)]
        for start in range(0,len(m),100000):
            ix=slice(start,start+100000);block=table[m.bill.to_numpy()[ix]]
            extra[ix,:5]=block
            extra[ix,5]=block[:,4]*x[ix,FEATURES.index('signed_analogue')]
            extra[ix,6]=block[:,4]*x[ix,FEATURES.index('sponsored_analogue')]
        # One vector per member/service term and release regime, reused across risk rows.
        missing=collections.Counter()
        for code,idx in m.groupby('member',sort=False).indices.items():
            mid=mids[int(code)];sub=m.iloc[idx];days=sub.day.to_numpy();sen=sub.senate.to_numpy()
            out=np.zeros((len(idx),len(DEMOGRAPHIC)),dtype=np.float32)
            out[:,5]=1;out[:,11]=1
            for t in terms.get(mid,[]):
                mask=(days>=t['lo'])&(days<t['hi'])&(sen==int(t['type']=='sen'))
                for after in [False,True]:
                    choose=mask & ((days>=RELEASE_2022)==after)
                    if not choose.any():continue
                    day=int(days[choose][0])
                    v=demographic_lookup(demo,cg,day,t['state'],t.get('district'),t['type']=='sen')
                    out[choose]=v
            extra[idx,len(TEXT):]=out
            missing['state_missing_rows']+=int(out[:,5].sum());missing['district_missing_rows']+=int(out[:,11].sum())
        extra.flush();del extra
        splits[cg]=dict(rows=len(m),sha256=digest(path),**missing)
        log(f'Text/demographic features {cg}: {splits[cg]}')
    write_json(OUT/'extra_feature_receipt.json',dict(completed_utc=stamp(),features=TEXT+DEMOGRAPHIC,text_features=TEXT,
         demographic_features=DEMOGRAPHIC,splits=splits,predecessor_audit_sha256=digest(OUT/'predecessor_audit_v2.json'),
         demographic_audit_sha256=digest(OUT/'demographics_audit_v2.json'),
         boundaries='117 NC district context excluded; 118 district context only from 2023-10-01; state context retained'))


if __name__=='__main__':build()
