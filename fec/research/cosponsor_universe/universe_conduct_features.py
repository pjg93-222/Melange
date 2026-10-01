"""Observed legislative conduct and dated activity, without latent personality labels."""
import collections
import datetime as dt

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from universe_common import OLD, OUT, digest, log, read_json, stamp, write_json
from build_panel import get_bills, get_members, term_at, ordinal

HISTORY=['conduct_log_sponsored','conduct_sponsored_finance_share','conduct_sponsored_enacted_share','conduct_sponsored_reported_share',
 'conduct_sponsored_passed_origin_share','conduct_sponsored_mean_log_coalition','conduct_crossparty_sponsor_share',
 'conduct_original_signature_share','conduct_delayed_signature_share','conduct_withdrawn_signature_share',
 'conduct_log_delay_median','conduct_log_delay_q25','conduct_log_delay_q75','conduct_join_within7_share',
 'conduct_join_within30_share','conduct_join_within90_share','conduct_topic_entropy','conduct_topics_covered_share',
 'conduct_sponsor_history_missing','conduct_cosponsor_history_missing','conduct_delayed_history_missing']
ACTIVITY=['activity_member_signs7_log','activity_member_signs30_log','activity_member_signs90_log',
 'activity_member_current_signs_log','activity_member_current_rate','activity_member_introductions30_log',
 'activity_chamber_introductions30_log','activity_chamber_signs30_log']
STAGES=['stage_passed_origin','stage_passed_other','stage_reported_origin','stage_failed_origin',
        'stage_days_since_origin_passage','stage_days_since_origin_report']


def stages(bill,day):
    """Numeric CRS action codes refer to the bill itself, excluding unrelated rule passage."""
    acts=[a for a in bill['actions'] if a['date'] and ordinal(a['date'])<day]
    codes=collections.defaultdict(list)
    for a in acts:codes[str(a['code'])].append(ordinal(a['date']))
    house=bill['chamber']=='House';passed='8000' if house else '17000';other='17000' if house else '8000'
    reported='5000' if house else '14000';failed='9000' if house else '18000'
    return [int(bool(codes[passed])),int(bool(codes[other])),int(bool(codes[reported])),int(bool(codes[failed])),
        min(366,day-max(codes[passed])) if codes[passed] else 366,min(366,day-max(codes[reported])) if codes[reported] else 366]


def history_rows(bills,members,cg):
    cutoff=dt.date(1789+2*(cg-1),1,3).toordinal();prior=[b for b in bills if b['congress']==cg-1]
    sponsored=collections.defaultdict(list);signed=collections.defaultdict(list)
    for b in prior:
        if b['intro']>=cutoff:continue
        sponsored[b['sponsor']].append(b)
        for c in b['cosponsors']:
            day=ordinal(c['date'])
            if day is not None and day<cutoff:signed[c['member']].append((b,c,day))
    rows=[]
    for mid in sorted(members):
        own=sponsored[mid];joins=signed[mid];delays=[day-b['intro'] for b,c,day in joins if day>b['intro']]
        topic=collections.Counter(b['topic'] for b,c,day in joins);total=len(joins)
        entropy=-sum((n/total)*np.log(n/total) for n in topic.values()) if total else 0
        cross=0;known=0
        for b,c,day in joins:
            mt=term_at(members[mid],day,b['chamber']);sp=members.get(b['sponsor']);st=term_at(sp,day,b['chamber']) if sp else None
            if mt and st and 'Unknown' not in [mt['party'],st['party']]:known+=1;cross+=mt['party']!=st['party']
        n=max(1,len(own));j=max(1,len(joins));d=max(1,len(delays))
        a=[np.log1p(len(own)),sum(b['finance_at_introduction'] for b in own)/n,
           sum(any(a['type']=='BecameLaw' and a['date'] and ordinal(a['date'])<cutoff for a in b['actions']) for b in own)/n,
           sum(stages(b,cutoff)[2] for b in own)/n,sum(stages(b,cutoff)[0] for b in own)/n,
           sum(np.log1p(sum(day<cutoff for day in b['joins'].values())) for b in own)/n,
           cross/max(1,known),sum(day==b['intro'] or c.get('original') for b,c,day in joins)/j,len(delays)/j,
           sum(bool(c.get('withdrawn') and ordinal(c['withdrawn'])<cutoff) for b,c,day in joins)/j,
           *([np.log1p(v) for v in np.quantile(delays,[.5,.25,.75])] if delays else [0,0,0]),
           sum(x<=7 for x in delays)/d,sum(x<=30 for x in delays)/d,sum(x<=90 for x in delays)/d,
           entropy,len(topic)/15,int(not own),int(not joins),int(not delays)]
        rows.append(dict(congress=cg,member=mid,**dict(zip(HISTORY,a))))
    return rows


def event_counts(dates,days,window=None):
    dates=np.asarray(dates,dtype=np.int32);days=np.asarray(days,dtype=np.int32)
    upper=np.searchsorted(dates,days,side='left')
    return upper if window is None else upper-np.searchsorted(dates,days-window,side='left')


def build():
    if (OUT/'conduct_receipt.json').exists():raise RuntimeError('Conduct features already frozen')
    bills=[b for b in get_bills() if b['congress']<=118];members,_=get_members();ident=read_json(OLD/'identifiers.json');bykey={b['key']:b for b in bills}
    rows=[];receipts={}
    for cg in [117,118]:
        rows+=history_rows(bills,members,cg)
        current=[b for b in bills if b['congress']==cg];signs=collections.defaultdict(list);intro=collections.defaultdict(list)
        chamber_intro=collections.defaultdict(list);chamber_sign=collections.defaultdict(list)
        for b in current:
            intro[b['sponsor']].append(b['intro']);chamber_intro[b['chamber']].append(b['intro'])
            for mid,day in b['joins'].items():signs[mid].append(day);chamber_sign[b['chamber']].append(day)
        for group in [signs,intro,chamber_intro,chamber_sign]:
            for k,v in group.items():group[k]=np.array(sorted(v),dtype=np.int32)
        m=pd.read_parquet(OLD/f'meta_{cg}.parquet');path=OUT/f'conduct_dynamic_{cg}.f32'
        result=np.memmap(path,mode='w+',dtype=np.float32,shape=(len(m),len(ACTIVITY)+len(STAGES)))
        cutoff=dt.date(1789+2*(cg-1),1,3).toordinal()
        for code,idx in m.groupby('member',sort=False).indices.items():
            mid=ident['members'][int(code)];days=m.day.to_numpy()[idx];events=signs.get(mid,[])
            cumulative=event_counts(events,days)
            result[idx,:6]=np.column_stack([np.log1p(event_counts(events,days,w)) for w in [7,30,90]]+
                [np.log1p(cumulative),cumulative/np.maximum(1,days-cutoff),np.log1p(event_counts(intro.get(mid,[]),days,30))])
        for ch,senate in [('House',0),('Senate',1)]:
            idx=np.flatnonzero(m.senate.to_numpy()==senate);days=m.day.to_numpy()[idx]
            result[idx,6:8]=np.column_stack([np.log1p(event_counts(chamber_intro[ch],days,30)),np.log1p(event_counts(chamber_sign[ch],days,30))])
        stage_positive=0
        for _,idx in m.groupby('group',sort=False).indices.items():
            first=m.iloc[idx[0]];b=bykey[ident['bills'][int(first.bill)]];block=stages(b,int(first.day))
            result[idx,8:]=block;stage_positive+=len(idx)*block[0]
        result.flush();del result;receipts[cg]=dict(rows=len(m),sha256=digest(path),rows_after_origin_passage=stage_positive)
        log(f'Observed conduct/activity/stages complete for Congress {cg}')
    pd.DataFrame(rows).to_csv(OUT/'conduct_history.csv',index=False)
    write_json(OUT/'conduct_receipt.json',dict(completed_utc=stamp(),history_features=HISTORY,activity_features=ACTIVITY,stage_features=STAGES,
         history_csv_sha256=digest(OUT/'conduct_history.csv'),dynamic_splits=receipts,source_bills_sha256=digest(OLD/'bills.jsonl'),
         qualification='Observed prior-Congress conduct and strictly earlier current activity, not personality. Official event dates reconstructed from frozen records. Original prior model type=Passage field is not reused: observed passage is CRS actionCode8000/17000.'))


if __name__=='__main__':
    with threadpool_limits(limits=2):build()
