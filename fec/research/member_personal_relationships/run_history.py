"""Evidence-first relationship assessment over the full, frozen work panel.

No trained 23-case classifier, probability claim, or negative geography weight.
The rules and all raw components are exposed for review.
"""
import json
from collections import Counter,defaultdict
from math import exp
import numpy as np
from .data import ROOT,read_json,write_json,write_ndjson,digest
from .prepare_history import OUT


def read_rows(path):
    if not path.exists():return []
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]


def number(v):
    return round(float(v),8) if v is not None and np.isfinite(v) else None


def compatibility(a,b):
    scores={t:exp(-abs(a[t]-b[t])) for t in 'OCEAN' if a.get(t) is not None and b.get(t) is not None}
    main=[scores[t] for t in 'EAO' if t in scores]
    return dict(traits=scores,EAO_similarity=sum(main)/len(main) if main else None,
                traits_observed=len(main))


def personality_expression(actor,traits,trait_percentiles,usage):
    """User-requested hypothesis: rare warmth from a less outwardly warm speaker
    is more distinctive. Only boosts *reviewed* positive evidence, not labels.
    """
    observed=[trait_percentiles[actor][t] for t in 'EA' if t in trait_percentiles[actor]]
    reserved=1-sum(observed)/len(observed) if observed else None
    total=sum(r.get('turns',0) for r in usage)
    warm=sum(r.get('warm_turns',0) for r in usage)
    rate=warm/total if total else None
    multiplier=1+(1-rate)*reserved if rate is not None and reserved is not None else 1.
    return dict(E=traits[actor].get('E'),A=traits[actor].get('A'),
        E_percentile=trait_percentiles[actor].get('E'),A_percentile=trait_percentiles[actor].get('A'),
        warm_turns=warm,turns=total,warm_turn_rate=rate,
        reviewed_warmth_distinctiveness_multiplier=multiplier,
        meaning='1–2 descriptive priority multiplier under the requested personality hypothesis; not sincerity probability')


def work_flag(row,threshold=.9):
    def ge(k,x):return row.get(k) is not None and row[k]>=x
    return (ge('shared_percentile',threshold) and (ge('direct_percentile',.75) or ge('network_percentile',threshold))
        and row['shared_bills']>=5 and row['shared_congresses']>=2)


def assess(row,events,expression):
    pos=[e for e in events if e['sign']=='positive'];neg=[e for e in events if e['sign']=='negative']
    explicit=[e for e in pos if e.get('evidence_level','personal_statement')=='personal_statement']
    cordial=[e for e in pos if e.get('evidence_level')=='contextual_warmth']
    families={e['source_family'] for e in pos}
    support=[]
    if row['work_flag']:support.append('selective_sustained_cooperation')
    if row.get('compatibility_support'):support.append('personality_compatibility')
    if row.get('network_percentile') is not None and row['network_percentile']>=.75:support.append('network_proximity')
    if len(families)>=2:support.append('repeated_reviewed_warmth')
    if pos and expression['reviewed_warmth_distinctiveness_multiplier']>=1.5:support.append('personality_conditioned_distinctive_warmth')
    friendship='unknown'
    if explicit:friendship='documented_personal_friendship'
    elif cordial and len(support)>=2:
        friendship='inferred_personal_affinity'
    elif row['work_flag']:friendship='cooperation_supported_candidate'
    hostility='documented_public_antagonism' if neg else 'unknown'
    # Dislike is inferred only from reviewed, person-directed antagonism; absence
    # of signatures, trait mismatch, and network distance never manufacture it.
    dislike='inferred_personal_dislike_at_event' if any(e.get('dislike_inference') for e in neg) else 'unknown'
    return dict(friendship=friendship,hostility=hostility,dislike=dislike,
        positive_episodes=len(families),negative_episodes=len({e['source_family'] for e in neg}),
        reviewed_warmth_strength=len(families)*expression['reviewed_warmth_distinctiveness_multiplier'],
        positive_support=support,
        evidence_ids=[e['evidence_id'] for e in events],
        latest_personal_evidence=max([e['event_date'] for e in events],default=None))


def load_all():
    members=read_json(OUT/'members.json');traits=read_json(OUT/'traits.json')
    ids=read_json(OUT/'matrix_index.json')['ids']
    with np.load(OUT/'work_matrices.npz') as z:w={k:z[k] for k in z.files}
    return members,traits,ids,w


def make_row(i,j,ids,members,traits,w):
    a,b=ids[i],ids[j];ma,mb=members[a],members[b]
    row=dict(actor=a,target=b,actor_name=ma['name'],target_name=mb['name'],
        same_party=ma['party']==mb['party'],same_state=ma['state']==mb['state'],
        same_chamber=ma['chamber']==mb['chamber'],
        ideology_distance=abs(ma['d1']-mb['d1']) if ma.get('d1') is not None and mb.get('d1') is not None else None)
    mapkeys=dict(direct_bills='direct',direct_opportunities='direct_opportunities',direct_propensity='direct_rate',
        direct_withdrawals='withdrawn_direct',shared_bills='shared',shared_active_bills='shared_active',
        shared_original_bills='original_shared',shared_opportunities='shared_opportunities',shared_propensity='shared_propensity',
        shared_jaccard='shared_jaccard',weighted_shared_jaccard='weighted_jaccard',
        shared_congresses='shared_congresses',shared_areas='shared_areas',
        co_service_congresses='co_service_congresses',peer_count='peer_count',
        shared_percentile='pct_weighted_jaccard',direct_percentile='pct_direct_rate',
        network_percentile='pct_network_proximity',network_proximity='network_proximity',issue_similarity='issue_similarity')
    row.update({name:number(w[key][i,j]) for name,key in mapkeys.items()})
    row['reverse_direct_bills']=number(w['direct'][j,i]);row['reverse_direct_propensity']=number(w['direct_rate'][j,i])
    row['reverse_shared_percentile']=number(w['pct_weighted_jaccard'][j,i])
    row['compatibility']=compatibility(traits[a],traits[b]);row['work_flag']=work_flag(row)
    row['by_congress']={str(c):dict(shared=int(w[f'c{c}_shared'][i,j]),
        direct=int(w[f'c{c}_direct'][i,j]),opportunities=int(w[f'c{c}_opportunities'][i,j]),
        shared_opportunities=int(w[f'c{c}_shared_opportunities'][i,j])) for c in range(116,120)}
    return row


def main():
    members,traits,ids,w=load_all();index={a:i for i,a in enumerate(ids)}
    base=read_rows(ROOT/'outputs/member_personal_relationships/20260910_anchored/anchor_events.ndjson')
    reviews=read_json(Path_here()/'history_reviews.json');names={p['name']:a for a,p in members.items()}
    extra=[]
    for episode in reviews['episodes']:
        for k,tie in enumerate(episode['ties']):
            extra.append(dict(evidence_id=f"history-{episode['id']}-{k}",actor=names[tie['actor']],target=names[tie['target']],
                actor_name=tie['actor'],target_name=tie['target'],sign='positive',event_date=episode['date'],
                source_family=episode['id'],episode_id=episode['id'],source_urls=[episode['url']],
                source_rowid=tie.get('source_rowid'),evidence_level=tie['level'],review_note=tie['note'],
                alternative_explanation=episode['context'],review_status='assistant_reviewed',attribution='direct_speaker'))
    events=base+extra
    # Strong person-directed action / selective refusal supports an event-dated
    # dislike inference; strategic dispute alone remains public antagonism.
    for e in events:
        if e.get('episode_id') in {'aoc_cruz_20210128','gosar_aoc_video_20211107','boebert_omar_202111'}:
            e['dislike_inference']=True
    pair_events=defaultdict(list)
    for e in events:
        if e.get('review_status')=='rejected':continue
        pair_events[(e['actor'],e['target'])].append(e)
    usages=defaultdict(list)
    for r in read_rows(OUT/'speaker_usage.ndjson'):usages[r['actor']].append(r)
    percentiles={a:{} for a in ids}
    for t in 'EA':
        values=np.array([traits[a][t] for a in ids if traits[a].get(t) is not None])
        for a in ids:
            if traits[a].get(t) is not None:
                v=traits[a][t];percentiles[a][t]=float(((values<v).sum()+.5*(values==v).sum())/len(values))
    expression={a:personality_expression(a,traits,percentiles,usages[a]) for a in ids}
    sims=[compatibility(traits[a],traits[b]) for i,a in enumerate(ids) for b in ids[i+1:]]
    compatibility_median=float(np.median([s['EAO_similarity'] for s in sims if s['traits_observed']>=2]))
    rhetoric=defaultdict(list)
    for r in read_rows(OUT/'pair_rhetoric.ndjson'):rhetoric[(r['actor'],r['target'])].append(r)
    selected=[];pair_lookup={}
    mask=(w['pct_weighted_jaccard']>=.9)&((w['pct_direct_rate']>=.75)|(w['pct_network_proximity']>=.9))
    mask&=(w['shared']>=5)&(w['shared_congresses']>=2)
    pairs=set(zip(*np.where(mask)))|{(index[a],index[b]) for a,b in pair_events if a in index and b in index}
    # Both directions retained for review, without copying directional evidence.
    pairs|={(j,i) for i,j in pairs}
    for i,j in sorted(pairs):
        row=make_row(i,j,ids,members,traits,w);a,b=ids[i],ids[j]
        row['compatibility_support']=(row['compatibility']['traits_observed']>=2 and row['compatibility']['EAO_similarity']>=compatibility_median)
        row.update(assess(row,pair_events[(a,b)],expression[a]));row['expression']=expression[a]
        row['rhetoric_by_source']=rhetoric[(a,b)]
        row['probability']=None;selected.append(row);pair_lookup[(a,b)]=row
    write_ndjson(OUT/'relationships.ndjson',selected);write_ndjson(OUT/'reviewed_events.ndjson',events)
    write_json(OUT/'personality_expression.json',expression)
    # Labels never enter work, network, matching, or thresholds. Test their work
    # ranks with all personal statements hidden, on the original frozen cases.
    cases=read_json(ROOT/'outputs/member_personal_relationships/20260910_anchored/anchor_cases.json')
    evaluations=[]
    for case in cases:
        values=[]
        for a,b in case['directions']:
            row=make_row(index[a],index[b],ids,members,traits,w)
            values.append(row)
        evaluations.append(dict(pair=case['pair'],sign=case['sign'],
            names=[members[a]['name'] for a in case['pair']],
            direct_percentile=mean_available([r['direct_percentile'] for r in values]),
            shared_percentile=mean_available([r['shared_percentile'] for r in values]),
            network_percentile=mean_available([r['network_percentile'] for r in values]),
            selected=any(r['work_flag'] for r in values),
            shared_bills=values[0]['shared_bills']))
    metrics={}
    for sign in ['positive','negative']:
        rr=[r for r in evaluations if r['sign']==sign]
        metrics[sign]=dict(pairs=len(rr),matched_shared_available=sum(r['shared_percentile'] is not None for r in rr),
            mean_shared_percentile=mean_available([r['shared_percentile'] for r in rr]),
            mean_direct_percentile=mean_available([r['direct_percentile'] for r in rr]),
            work_flags=sum(r['selected'] for r in rr))
    metrics['interpretation']='Retrospective label-hidden check; not an independent population accuracy or prospective forecast.'
    metrics['sensitivity']={str(t):int(((w['pct_weighted_jaccard']>=t)&((w['pct_direct_rate']>=.75)|(w['pct_network_proximity']>=t))&(w['shared']>=5)&(w['shared_congresses']>=2)).sum()) for t in [.85,.9,.95]}
    write_json(OUT/'benchmark.json',dict(metrics=metrics,cases=evaluations))
    counts=dict(Counter(r['friendship'] for r in selected))
    write_json(OUT/'results.json',dict(work=read_json(OUT/'work_manifest.json'),speech=read_json(OUT/'speech_manifest.json'),
        friendship_directions=counts,hostility_directions=sum(r['hostility']!='unknown' for r in selected),
        dislike_inferences=sum(r['dislike']!='unknown' for r in selected),compatibility_median=compatibility_median,benchmark=metrics,
        source_inputs_unchanged=all(digest(ROOT/p)==h for p,h in read_json(OUT/'work_manifest.json')['source_sha256'].items())))
    print(json.dumps(dict(counts=counts,benchmark=metrics)),flush=True)


def mean_available(values):
    v=[x for x in values if x is not None and np.isfinite(x)]
    return sum(v)/len(v) if v else None


def Path_here():
    from pathlib import Path
    return Path(__file__).parent


if __name__=='__main__':main()
