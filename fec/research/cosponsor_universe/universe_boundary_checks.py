"""Focused adversarial checks for timing, identity joins and null-source treatment."""
import datetime as dt
import numpy as np

from universe_common import OUT, digest, stamp, write_json
from universe_conduct_features import stages,event_counts
from universe_relational_panel import exposure
from universe_psychology_features import self_test as language_checks
from universe_election_features import self_test as election_checks
from universe_models import Panel, menu, LANGUAGE, ELECTION


def run():
    language_checks();election_checks();checks=[]
    day=dt.date(2021,5,1).toordinal()
    assert event_counts([day-31,day-30,day-1,day,day+1],[day],30).tolist()==[2]
    assert event_counts([day-1,day,day+1],[day]).tolist()==[1]
    assert event_counts([],[day],30).tolist()==[0];checks.append('strict_activity_window_and_empty_source')
    bill=dict(chamber='House',actions=[dict(date='2021-05-01',code='8000'),dict(date='2021-04-30',code='H1L220'),
                                     dict(date='2021-05-02',code='5000')])
    assert stages(bill,day)==[0,0,0,0,366,366];checks.append('same_day_future_and_unrelated_rule_exclusion')
    assert stages(bill,day+1)==[1,0,0,0,1,366];checks.append('earlier_bill_passage_inclusion')
    bill['chamber']='Senate'
    assert stages(bill,day+1)[:4]==[0,1,0,0];checks.append('origin_and_other_chamber_separation')
    a=np.array([[0,.5,.5],[.5,0,0],[.5,0,0]],dtype=np.float32)
    e,m=exposure(a,np.array([0,1,2]),[1]);assert np.allclose(e,[.5,0,0]) and np.allclose(m,[.5,0,0])
    e,m=exposure(a,np.arange(3),[]);assert np.all(e==0) and np.all(m==0);checks.append('normalized_graph_exposure_and_empty_coalition')
    specs=menu();assert len(specs)==24 and not any('119' in f for s in specs.values() for f in s['features'])
    assert sum(s['historical_selection_eligible'] for s in specs.values())==23
    assert sum(s['role']=='refit_control' for s in specs.values())==8
    checks.append('all_controls_refit_and_placebo_excluded_from_selection')
    panels={}
    for cg in [117,118]:
        p=Panel(cg);gold_idx=np.flatnonzero(p.gold)
        idx=gold_idx[np.unique(np.linspace(0,len(gold_idx)-1,2001).astype(int))]
        names=specs['boosted_universe']['features'];x=p.design(idx,names)
        assert np.isfinite(x).all();assert len(set(names))==len(names)
        real=p.design(idx,ELECTION);sham=p.design(idx,ELECTION,True);assert np.array_equal(real,sham)
        groups=p.meta[p.gold].groupby('member').senate.agg(['min','max'])
        for _,block in groups.groupby(['min','max']):
            mi=block.index.to_numpy(dtype=int);assert set(mi)==set(p.permutation[mi])
            for name in LANGUAGE:assert np.array_equal(np.sort(p.static[name][mi]),np.sort(p.static[name][p.permutation[mi]]))
        assert groups.index.nunique()==377
        panels[cg]=dict(full_rows=len(p.meta),cohort_rows=int(p.gold.sum()),cohort_members=groups.index.nunique(),sampled_rows=len(idx),features=len(names),missing_static_rows=p.missing)
    checks+=['complete_panel_left_join','finite_feature_values','unique_feature_names','placebo_preserves_strata_and_marginals','placebo_changes_only_language']
    write_json(OUT/'universe_boundary_checks.json',dict(completed_utc=stamp(),status='PASS',checks=checks,panels=panels,
       source_language_self_tests=13,source_election_self_tests='PASS',code_sha256=digest(__file__)))
    print('PASS:',len(checks),'pipeline boundary checks plus language/election source checks')


if __name__=='__main__':run()
