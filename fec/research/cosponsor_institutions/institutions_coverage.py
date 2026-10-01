"""Descriptive source coverage in the fixed cohort; reads no outcome labels."""
import datetime as dt
import numpy as np
import pandas as pd
from institutions_common import OLD, OUT, UNIVERSE, digest, read_json, write_json, stamp


def run():
    ids=read_json(OLD/'identifiers.json')['members'];gold=set(read_json(UNIVERSE/'gold_cohort.json')['member_ids'])
    membership=np.array([m in gold for m in ids]);result={}
    specs={'caucus':{'leadership_observed':'caucus_leadership_lag_groups_log',
                    'membership_observed':'caucus_membership_observed_groups_log',
                    'membership_source_released':'caucus_membership_source_available'},
           'committees':{'member_assignment_observed':'committee_member_roster_observed',
                         'prior_referral_match':'committee_member_referred_any',
                         'prior_bill_meeting_observed':'committee_bill_past_meeting_count_log1p'},
           'votes':{'prior_topic_vote_observed':'vote_topic_eligible_log',
                    'sponsor_topic_comparison_observed':'vote_sponsor_topic_shared_recorded_log',
                    'same_bill_vote_observed':'vote_same_bill_earlier_eligible_log'}}
    for cg in [117,118]:
        meta=pd.read_parquet(OLD/f'meta_{cg}.parquet',columns=['member','day','mature'])
        mask=membership[meta.member.to_numpy()]&meta.mature.to_numpy().astype(bool)
        periods={'training_117':mask} if cg==117 else {
            'forecast_dates_2023':mask&(meta.day.to_numpy()<dt.date(2024,1,1).toordinal()),
            'forecast_dates_2024':mask&(meta.day.to_numpy()>=dt.date(2024,1,1).toordinal())}
        for period,pick in periods.items():result[period]={'rows':int(pick.sum()),'members':int(meta.member[pick].nunique()),'blocks':{}}
        for block,fields in specs.items():
            names=read_json(OUT/f'{block}_receipt.json')['features']
            array=np.memmap(OUT/f'{block}_{cg}.f32',dtype='float32',mode='r',shape=(len(meta),len(names)))
            for period,pick in periods.items():
                counts={}
                for label,name in fields.items():
                    observed=pick&(array[:,names.index(name)]>0)
                    counts[label]={'rows':int(observed.sum()),'fraction':float(observed.sum()/pick.sum()),'members':int(meta.member[observed].nunique())}
                result[period]['blocks'][block]=counts
            del array
    write_json(OUT/'cohort_feature_coverage.json',dict(created_utc=stamp(),periods=result,
        source_receipts={b:digest(OUT/f'{b}_receipt.json') for b in specs},
        qualification='Observed positive evidence and source release coverage, not source completeness, continuous membership, endorsement or absence of action. No labels read. Training coverage includes all mature gold risk rows before negative sampling.'))
    print('Fixed-cohort source coverage written')


if __name__=='__main__':run()
