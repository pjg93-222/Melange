"""Dated public lobbying attention and explicitly provisional staff sensitivity."""
import collections
import csv
import datetime as dt
import gzip
import itertools
import json
import os

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from common import OLD, OUT, ROOT, digest, log, read_json, stamp, write_json
from build_panel import get_bills, ordinal

LOBBY=['lobby_log_filings','lobby_log_clients','lobby_log_registrants','lobby_log_named_people',
       'lobby_log_filings_90d','lobby_days_since_latest','lobby_days_since_first','lobby_observed']
STAFF=['provisional_staff_log_people','provisional_staff_log_office_links','provisional_staff_sponsor_link',
       'provisional_staff_active_share','provisional_staff_recent_30d_share','provisional_staff_coverage']


def union_days(intervals):
    end=None;total=0
    for lo,hi in sorted(intervals):
        if hi<=lo:continue
        if end is None or lo>end:total+=hi-lo
        else:total+=max(0,hi-end)
        end=max(end or hi,hi)
    return total


def staff_graph(episodes,cg,mids):
    cutoff=dt.date(1789+2*(cg-1),1,3).toordinal();index={mid:i for i,mid in enumerate(mids)}
    intervals=collections.defaultdict(list)
    for row in episodes:
        mid=row.get('member_bioguide_id')
        lo,hi=ordinal(row.get('start_latest')),ordinal(row.get('end_earliest'))
        if mid not in index or lo is None or hi is None or lo>=cutoff:continue
        if row['identity_status']!='ACCEPTED' or row['container_status']!='ACCEPTED':continue
        intervals[(row['resolved_person_id'],mid)].append((lo,min(hi,cutoff)))
    people=collections.defaultdict(set);office=collections.defaultdict(set)
    for (person,mid),ints in intervals.items():
        if union_days(ints)>=30:people[person].add(mid);office[mid].add(person)
    a=np.zeros((len(mids),len(mids)),dtype=np.float32)
    for offices in people.values():
        for left,right in itertools.combinations(sorted(offices),2):
            i,j=index[left],index[right];a[i,j]+=1;a[j,i]+=1
    counts=np.array([len(office[mid]) for mid in mids],dtype=np.float32)
    denom=np.sqrt(counts[:,None]*counts[None,:]);a=np.divide(a,denom,out=np.zeros_like(a),where=denom>0)
    transition=np.divide(a,a.sum(axis=1)[:,None],out=np.zeros_like(a),where=a.sum(axis=1)[:,None]>0)
    return a,transition,counts


def filing_available_day(filing,posted):
    dates=[d for d in [ordinal(filing),ordinal(posted)] if d is not None]
    return max(dates) if dates else None


def build():
    if (OUT/'external_context_receipt.json').exists():raise RuntimeError('External context already frozen')
    lda=__import__('pathlib').Path(os.environ['LOCALAPPDATA'])/'Melange/lda_rebuild/derived/interactions/interaction_ledger.csv'
    before=digest(lda);events=collections.defaultdict(dict);audit=collections.Counter()
    with lda.open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            if not row['bill_key'].startswith(('117:','118:')):continue
            audit['rows_scanned']+=1
            if row['channel']!='formal_strict':audit['nonformal_excluded']+=1;continue
            day=filing_available_day(row['filing_date'],row['dt_posted'])
            if day is None:audit['undated_excluded']+=1;continue
            key=(row['filing_uuid'],row['lob_id']);b=row['bill_key']
            record=events[b].setdefault(key,dict(day=day,filing=row['filing_uuid'],client=row['lob_id'],registrant=row['registrant_name'],people=set()))
            record['day']=max(record['day'],day);record['people'].update(x.strip() for x in row['lobbyists'].split('|') if x.strip())
    if digest(lda)!=before:raise RuntimeError('Interaction ledger changed while reading')
    episode_path=ROOT/'audits/staffer_network/employment_promotion_generation_20260901_v5_primary/canonical_employment_episodes.ndjson.gz'
    episode_hash=digest(episode_path)
    with gzip.open(episode_path,'rt',encoding='utf-8') as f:episodes=[json.loads(line) for line in f]
    ident=read_json(OLD/'identifiers.json');mids=ident['members'];keys=ident['bills'];mi={mid:i for i,mid in enumerate(mids)}
    bills={b['key']:b for b in get_bills() if b['congress'] in [117,118]}
    splits={}
    for cg in [117,118]:
        a,p,counts=staff_graph(episodes,cg,mids)
        np.savez_compressed(OUT/f'provisional_staff_graph_{cg}.npz',adjacency=a,people=counts,members=mids)
        m=pd.read_parquet(OLD/f'meta_{cg}.parquet');path=OUT/f'external_{cg}.f32'
        extra=np.memmap(path,mode='w+',dtype=np.float32,shape=(len(m),len(LOBBY+STAFF)))
        covered=collections.Counter()
        for group,idx in m.groupby('group',sort=False).indices.items():
            rows=m.iloc[idx];key=keys[int(rows.bill.iloc[0])];day=int(rows.day.iloc[0]);b=bills[key]
            earlier=[r for r in events.get(key,{}).values() if r['day']<day]
            latest=max((r['day'] for r in earlier),default=day-365)
            first=min((r['day'] for r in earlier),default=day-365)
            vals=[np.log1p(len({r['filing'] for r in earlier})),np.log1p(len({r['client'] for r in earlier})),
                  np.log1p(len({r['registrant'] for r in earlier})),np.log1p(len(set().union(*(r['people'] for r in earlier)))),
                  np.log1p(len({r['filing'] for r in earlier if r['day']>=day-90})),min(365,day-latest),min(365,day-first),bool(earlier)]
            extra[idx,:len(LOBBY)]=vals
            active=np.zeros(len(mids),dtype=np.float32);recent=active.copy()
            for mid,d in b['joins'].items():
                if mid in mi and d<day:active[mi[mid]]=1;recent[mi[mid]]=d>=day-30
            if b['intro']<day and b['sponsor'] in mi:active[mi[b['sponsor']]]=1
            codes=rows.member.to_numpy();sponsor=mi.get(b['sponsor'])
            features=np.column_stack([np.log1p(counts[codes]),np.log1p((a[codes]>0).sum(axis=1)),
                a[codes,sponsor] if sponsor is not None else np.zeros(len(codes)),p[codes]@active,p[codes]@recent,counts[codes]>0])
            extra[idx,len(LOBBY):]=features
            covered['lobby_attention_rows']+=len(idx)*bool(earlier);covered['staff_history_rows']+=int((counts[codes]>0).sum())
        extra.flush();del extra
        splits[cg]=dict(rows=len(m),sha256=digest(path),**covered)
        log(f'External context {cg}: {splits[cg]}')
    write_json(OUT/'external_context_receipt.json',dict(completed_utc=stamp(),features=LOBBY+STAFF,lobby_features=LOBBY,
        staff_features=STAFF,splits=splits,lobby_audit=dict(audit),lobby_bills=len(events),
        source_receipts=[dict(path=str(lda),sha256=before),dict(path=str(episode_path),sha256=episode_hash)],
        staff_status='QUARANTINED_EXPLORATORY_ONLY',staff_excluded_from_primary_selection=True,
        qualification='Provisional employment assertions, incomplete source coverage and unresolved corpus-level identity gates. Staff sensitivity is not validated staff influence.',
        lobbying_qualification='Dated public bill-level filing attention only, no member-contact treatment and no sign-derived lobbying flag.'))


if __name__=='__main__':
    with threadpool_limits(limits=1):build()
