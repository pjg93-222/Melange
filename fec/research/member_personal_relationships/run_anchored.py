"""Fit and evaluate the second pilot; all writes stay in an isolated output folder."""
from collections import Counter,defaultdict
import hashlib,itertools,json,math,random,re
from pathlib import Path
import numpy as np
from .data import ROOT,REFERENCE,context,context_key,read_json,write_json,write_ndjson,digest
from .core import accepted_events,collapse_episodes,graph_features,personality_features
from .run import read_lines,personality_comparisons
from .work import eligible_members,raw_pairs,build_residuals
from .anchored_model import Logistic,ResidualRanker,anchor_cases,fold_mask,rank_fraction,sign_metrics

HERE=Path(__file__).parent
BASE=ROOT/'outputs/member_personal_relationships/20260910_pilot'
OUT=ROOT/'outputs/member_personal_relationships/20260910_anchored'
CUTOFF='2026-09-10'
SEED=20260910
CONTROL_NAMES=['same_party','same_state','same_chamber','nominate_distance','d2_distance',
               'ego_leader','alter_leader','ego_senate','alter_senate','tenure_difference',
               'committee_jaccard','shared_committee_count']
MOTIFS=[f'{a}_{b}_{s}{t}' for a in ['out','in'] for b in ['out','in'] for s in '+-' for t in '+-']
NETWORK_NAMES=['positive_resource_allocation','inverse_positive_path']+['motif_'+k for k in MOTIFS]
# Degree/popularity counts are nuisance controls, never personal-affinity evidence.
DEGREES=[f'{who}_{sign}_{direction}degree' for sign in ['positive','negative']
         for who in ['ego','alter'] for direction in ['out','in']]
WORK_NAMES=['work_shrunk_residual','reverse_work_shrunk_residual','work_7day_shrunk_residual']
TRAIT_NAMES=['personality_similarity_excess','ego_extraversion','alter_agreeableness']
FEATURE_NAMES=WORK_NAMES+NETWORK_NAMES


def anchors(members):
    catalog=read_json(HERE/'anchor_catalog.json')
    byname={p['name']:a for a,p in members.items()}
    # The prior pilot contains both accepted and rejected reviews; only accepted
    # personal evidence is carried forward, never all reviewed retrievals.
    events=accepted_events(read_lines(BASE/'events.ndjson'),CUTOFF)
    for e in events:
        e['review_note']=e.get('reason','')
        e['source_urls']=[e.get('official_source_url') or e.get('source_url') or
                         'https://www.govinfo.gov/content/pkg/'+e['package']+'/pdf/'+e['package']+'-house.pdf']
        if e['actor_name']=='Mike Lee':
            e['source_urls']=['https://www.govinfo.gov/content/pkg/CREC-2025-05-14/pdf/CREC-2025-05-14.pdf']
    for episode in catalog['episodes']:
        for i,tie in enumerate(episode['ties']):
            a,b=byname[tie['actor']],byname[tie['target']]
            events.append(dict(evidence_id=f"anchor-{episode['id']}-{i}",actor=a,target=b,
                actor_name=tie['actor'],target_name=tie['target'],sign=tie['sign'],category=tie['category'],
                event_date=episode['event_date'],published_date=episode['published_date'],
                date_basis=episode.get('date_basis','source-dated event'),
                source_family=episode['id'],episode_id=episode['id'],source_urls=episode['urls'],
                source_rowid=episode.get('source_rowid'),review_status='assistant_reviewed',
                attribution=tie.get('attribution','direct_speaker'),review_note=tie['note'],
                alternative_explanation=episode['context'],naturalness='context_reviewed_not_scored'))
    return accepted_events(events,CUTOFF),catalog


def committee_memberships():
    """Read only top-level four-letter committee codes from the frozen YAML.

    Explicitly validate the limited syntax consumed; no YAML execution or import
    of existing builders. Subcommittee identifiers are intentionally ignored.
    """
    memberships=defaultdict(set);code=None
    for line in (REFERENCE/'committee-membership-current.yaml').read_text(encoding='utf-8').splitlines():
        if line and not line[0].isspace() and not line.startswith('-'):
            match=re.fullmatch(r'([A-Z0-9]+):(?: \[\])?',line)
            if not match: raise ValueError('Unexpected committee header: '+line)
            code=match[1]
        match=re.fullmatch(r'  bioguide: ([A-Z]\d{6})',line)
        if match and code and len(code)==4: memberships[match[1]].add(code)
    if len(memberships)<400: raise ValueError('Committee mapping unexpectedly sparse')
    return memberships


def context_vector(a,b,members,committees):
    x,y=members[a],members[b];f=context(x,y)
    union=committees[a]|committees[b];common=committees[a]&committees[b]
    tenure=lambda m:(2026-int(min(t['start'] for t in m['terms'])[:4]))/10
    d2=abs(x['d2']-y['d2']) if x.get('d2') is not None and y.get('d2') is not None else None
    return [f['same_party'],f['same_state'],f['same_chamber'],f['nominate_distance'],d2,
            x['leader'],y['leader'],x['chamber']=='Senate',y['chamber']=='Senate',
            abs(tenure(x)-tenure(y)),len(common)/len(union) if union else 0,len(common)]


def controls_for(a,b,members,known):
    # Fix the actor and match target chamber, party relation, state relation,
    # NOMINATE-distance bin and leadership status. No use of relationship label.
    candidates=[c for c in sorted(members) if c!=a and tuple(sorted((a,c))) not in known
                and context_key(members[a],members[c])==context_key(members[a],members[b])
                and members[c]['chamber']==members[b]['chamber']]
    rng=random.Random(f'{SEED}:{a}:{b}')
    rng.shuffle(candidates)
    return [(a,c) for c in candidates[:10]]


def number(x): return float(x) if x is not None else 0.


class Features:
    def __init__(self,members,traits,work,personality,committees,events):
        self.members=members;self.traits=traits;self.work=work
        self.personality=personality;self.committees=committees;self.events=events
    def row(self,pair,graph):
        a,b=pair;w=self.work.get(pair,{});rw=self.work.get((b,a),{})
        family={e['source_family'] for e in graph if {e['actor'],e['target']}=={a,b}}
        g=graph_features(graph,a,b,as_of=CUTOFF,excluded_families=family)
        def shrink(w,key):
            n=w.get('work_opportunities',0)
            return number(w.get(key))*n/(n+20)
        wf=[shrink(w,'work_residual_rate'),shrink(rw,'work_residual_rate'),shrink(w,'work_residual_rate_7')]
        nf=[g['positive_resource_allocation'],1/g['positive_shortest_path'] if g['positive_shortest_path'] else 0]
        nf += [math.log1p(g['signed_motifs'][k]) for k in MOTIFS]
        pf=personality_features(self.traits[a],self.traits[b])
        tf=[self.personality[pair]['personality_similarity_excess'],pf['ego_extraversion'],pf['alter_agreeableness']]
        c=context_vector(a,b,self.members,self.committees)+[math.log1p(g[k]) for k in DEGREES]
        return c,wf+nf,tf,g


def dataset(cases,background,featurizer,graph,sign=None,excluded=()):
    crows=[];xrows=[];trows=[];ys=[];weights=[]
    for case in cases:
        if sign is not None and case['sign']!=sign: continue
        for pair in map(tuple,case['directions']):
            c,x,t,_=featurizer.row(pair,graph)
            crows.append(c);xrows.append(x);trows.append(t)
            ys.append(int(case['sign']=='positive') if sign is None else 1)
            weight=1/len(case['directions']);weights.append(weight)
            if sign is not None:
                peers=[p for p in background[pair] if tuple(sorted(p)) not in excluded]
                if not peers:
                    crows.pop();xrows.pop();trows.pop();ys.pop();weights.pop();continue
                for peer in peers:
                    c,x,t,_=featurizer.row(peer,graph)
                    crows.append(c);xrows.append(x);trows.append(t);ys.append(0);weights.append(weight/len(peers))
    return np.asarray(crows,float),np.asarray(xrows,float),np.asarray(trows,float),np.asarray(ys),weights


def evaluate(cases,events,background,featurizer):
    predictions=[];retrieval=[];audit=[]
    for i,held in enumerate(cases):
        graph,train=fold_mask(events,cases,held)
        c,x,t,y,w=dataset(train,background,featurizer,graph)
        base=Logistic().fit(c[:,:len(CONTROL_NAMES)],y,w)
        full=Logistic().fit(np.column_stack([c,x]),y,w)
        no_network=Logistic().fit(np.column_stack([c,x[:,:len(WORK_NAMES)]]),y,w)
        no_work=Logistic().fit(np.column_stack([c,x[:,len(WORK_NAMES):]]),y,w)
        trait=Logistic().fit(np.column_stack([c,x,t]),y,w)
        out=dict(pair=held['pair'],sign=held['sign'],directions=held['directions'])
        ctest=[];xtest=[];ttest=[]
        for p in map(tuple,held['directions']):
            ci,xi,ti,_=featurizer.row(p,graph);ctest.append(ci);xtest.append(xi);ttest.append(ti)
        out['context_baseline']=float(base.predict(np.asarray(ctest)[:,:len(CONTROL_NAMES)]).mean())
        out['indirect_strict']=float(full.predict(np.column_stack([ctest,xtest])).mean())
        out['no_network']=float(no_network.predict(np.column_stack([ctest,np.asarray(xtest)[:,:len(WORK_NAMES)]])).mean())
        out['no_work']=float(no_work.predict(np.column_stack([ctest,np.asarray(xtest)[:,len(WORK_NAMES):]])).mean())
        out['personality_sensitivity']=float(trait.predict(np.column_stack([ctest,xtest,ttest])).mean())
        predictions.append(out)
        excluded={tuple(sorted(p)) for p in held['directions']}
        for p in map(tuple,held['directions']): excluded.update(tuple(sorted(q)) for q in background[p])
        pc,px,pt,py,pw=dataset(train,background,featurizer,graph,held['sign'],excluded)
        ranker=ResidualRanker().fit(pc,px,py,pw)
        profile=ResidualRanker().fit(pc,np.column_stack([px,pt]),py,pw)
        for pair in map(tuple,held['directions']):
            peers=background[pair]
            if len(peers)<3: continue
            rc=[];rx=[];rt=[]
            for p in [pair]+peers:
                ci,xi,ti,_=featurizer.row(p,graph);rc.append(ci);rx.append(xi);rt.append(ti)
            scores=ranker.score(rc,rx);ps=profile.score(rc,np.column_stack([rx,rt]))
            rank,pct=rank_fraction(scores[0],scores[1:]);prank,ppct=rank_fraction(ps[0],ps[1:])
            retrieval.append(dict(actor=pair[0],target=pair[1],sign=held['sign'],n_unlabeled=len(peers),
                rank=rank,percentile=pct,profile_rank=prank,profile_percentile=ppct,
                anchor_score=float(scores[0]),controls=[dict(actor=p[0],target=p[1],score=float(s)) for p,s in zip(peers,scores[1:])]))
        trainpairs={tuple(c['pair']) for c in train}
        removedfamilies=set().union(*(set(c['families']) for c in cases if tuple(c['pair']) not in trainpairs))
        assert not any(tuple(sorted((e['actor'],e['target'])))==tuple(held['pair']) for e in graph)
        assert not any(e['source_family'] in removedfamilies for e in graph)
        audit.append(dict(held_pair=held['pair'],training_pairs=len(train),removed_families=sorted(removedfamilies),
                          graph_evidence_rows=len(graph),test_pairs_excluded_from_PU_training=len(excluded)))
        print(f'Fold {i+1}/{len(cases)} complete',flush=True)
    return predictions,retrieval,audit


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    inputs=[BASE/'members.json',BASE/'traits.json',BASE/'bills.ndjson',BASE/'events.ndjson',
            BASE/'pair_features.ndjson',HERE/'anchor_catalog.json',REFERENCE/'committee-membership-current.yaml']
    before={str(p.relative_to(ROOT)):digest(p) for p in inputs}
    members=read_json(BASE/'members.json');traits=read_json(BASE/'traits.json')
    events,catalog=anchors(members);cases=anchor_cases(events,CUTOFF)
    known={tuple(c['pair']) for c in cases};background={}
    for case in cases:
        for a,b in case['directions']: background[(a,b)]=controls_for(a,b,members,known)
    committees=committee_memberships()
    pairs={(r['actor'],r['target']) for r in read_lines(BASE/'pair_features.ndjson')}
    pairs.update(p for peers in background.values() for p in peers)
    pairs.update(background)
    # Include two-hop personal-network candidates, then add a reproducible random
    # panel. The scored set is deliberately bounded, not claimed as all Congress.
    neighbors=defaultdict(set)
    for e in events:
        neighbors[e['actor']].add(e['target']);neighbors[e['target']].add(e['actor'])
    for friends in neighbors.values(): pairs.update(itertools.permutations(sorted(friends),2))
    rng=random.Random(SEED);ids=sorted(members)
    for _ in range(600): pairs.add(tuple(rng.sample(ids,2)))
    pairs.update((b,a) for a,b in list(pairs))
    pairs=sorted(pairs)
    print(f'{len(cases)} anchor pairs, {len(events)} source-reviewed directions/episodes, {len(pairs)} scored directions',flush=True)
    bills=read_lines(BASE/'bills.ndjson');eligibility=eligible_members(members,bills)
    work,opportunities=build_residuals(members,bills,pairs,eligibility)
    print('Matched work baselines complete',flush=True)
    personality=personality_comparisons(members,traits)
    featurizer=Features(members,traits,work,personality,committees,events)
    predictions,retrieval,audit=evaluate(cases,events,background,featurizer)
    models={};rankers={}
    for sign in ['positive','negative']:
        c,x,t,y,w=dataset(cases,background,featurizer,events,sign)
        ranker=ResidualRanker().fit(c,x,y,w)
        profile=ResidualRanker().fit(c,np.column_stack([x,t]),y,w)
        rankers[sign]=(ranker,profile)
        models[sign]=dict(strict=ranker.serializable(),personality_sensitivity=profile.serializable(),
                          training_rows=len(y),selected_rows=int(y.sum()),unlabeled_rows=int((y==0).sum()))
    rows=[]
    for pair in pairs:
        a,b=pair;c,x,t,g=featurizer.row(pair,events)
        row=dict(actor=a,target=b,actor_name=members[a]['name'],target_name=members[b]['name'],
                 **context(members[a],members[b]),**personality[pair],**work[pair],**g)
        own=collapse_episodes([e for e in events if (e['actor'],e['target'])==pair])
        row['positive_episodes']=sum(e['sign']=='positive' for e in own)
        row['negative_episodes']=sum(e['sign']=='negative' for e in own)
        row['evidence_ids']=[e['evidence_id'] for e in own]
        row['latest_evidence']=max((e['event_date'] for e in own),default=None)
        row['affinity_probability']=None;row['antagonism_probability']=None
        for sign,label in [('positive','affinity'),('negative','antagonism')]:
            strict,profile=rankers[sign]
            row[label+'_score']=float(strict.score([c],[x])[0])
            row[label+'_profile_score']=float(profile.score([c],[x+t])[0])
            network_indices=range(len(WORK_NAMES),len(FEATURE_NAMES))
            row[label+'_network_contribution']=float(strict.contribution([c],[x],network_indices)[0])
            row[label+'_observed_supported_network']=any(strict.anchor_supported_[i] and abs(x[i])>1e-10 for i in network_indices)
        rows.append(row)
    unknown=[r for r in rows if tuple(sorted((r['actor'],r['target']))) not in known]
    for sign,label in [('positive','affinity'),('negative','antagonism')]:
        order=sorted(unknown,key=lambda r:(-r[label+'_score'],r['actor'],r['target']))
        for rank,row in enumerate(order,1): row[label+'_rank']=rank
    for r in rows:
        channels=sum([number(r['work_residual_rate'])>0,number(r['personality_similarity_excess'])>0,r['positive_resource_allocation']>0])
        knownpair=tuple(sorted((r['actor'],r['target']))) in known
        r['affinity_status']='documented_affinity' if r['positive_episodes'] else (
            'inferred_friendship_candidate' if not knownpair and r.get('affinity_rank',99999)<=50
            and r['affinity_score']>0 and r['affinity_profile_score']>0 and channels>=2 else 'unresolved')
        r['antagonism_status']='documented_personal_antagonism' if r['negative_episodes'] else (
            'inferred_antagonism_candidate' if not knownpair and r.get('antagonism_rank',99999)<=20
            and r['antagonism_score']>0 and r['antagonism_profile_score']>0
            and r['antagonism_observed_supported_network'] and r['antagonism_network_contribution']>0
            and any(v for k,v in r['signed_motifs'].items() if '-' in k) else 'unresolved')
        r['confidence']='source_reviewed_working_label' if r['evidence_ids'] else 'exploratory_inference'
    # Separate evaluation on members absent from the training anchors. This
    # exposes how much the pair holdout depends on relationships already known
    # about those same members. No inferred edge is ever added to the graph.
    member_disjoint=[]
    for held in cases:
        nodes=set(held['pair'])
        synthetic=dict(held,families=sorted(set().union(*(set(c['families']) for c in cases if nodes.intersection(c['pair'])))))
        graph,train=fold_mask(events,cases,synthetic)
        c,x,t,y,w=dataset(train,background,featurizer,graph)
        base=Logistic().fit(c[:,:len(CONTROL_NAMES)],y,w)
        full=Logistic().fit(np.column_stack([c,x]),y,w)
        test=[featurizer.row(tuple(p),graph) for p in held['directions']]
        cc=[r[0] for r in test];xx=[r[1] for r in test]
        assert all(not nodes.intersection(c['pair']) for c in train)
        assert all(not nodes.intersection([e['actor'],e['target']]) for e in graph)
        member_disjoint.append(dict(pair=held['pair'],sign=held['sign'],training_pairs=len(train),
            context_baseline=float(base.predict(np.asarray(cc)[:,:len(CONTROL_NAMES)]).mean()),
            indirect_strict=float(full.predict(np.column_stack([cc,xx])).mean())))
    results=dict(as_of=CUTOFF,anchor_pairs=len(cases),anchor_signs=dict(Counter(c['sign'] for c in cases)),
        reviewed_evidence_rows=len(events),deduplicated_source_families=len({e['source_family'] for e in events}),
        directed_anchor_ties=len({(e['actor'],e['target']) for e in events}),scored_directions=len(rows),
        same_party_negative_pairs=sum(c['sign']=='negative' and members[c['pair'][0]]['party']==members[c['pair'][1]]['party'] for c in cases),
        cross_party_positive_pairs=sum(c['sign']=='positive' and members[c['pair'][0]]['party']!=members[c['pair'][1]]['party'] for c in cases),
        sign_evaluation={key:sign_metrics(predictions,key) for key in ['context_baseline','indirect_strict','no_network','no_work','personality_sensitivity']},
        member_disjoint_evaluation={key:sign_metrics(member_disjoint,key) for key in ['context_baseline','indirect_strict']},
        retrieval={},affinity_statuses=dict(Counter(r['affinity_status'] for r in rows)),
        antagonism_statuses=dict(Counter(r['antagonism_status'] for r in rows)),
        qualification='Retrospective, purposively ascertained, assistant-reviewed anchors. No population probability or causal identification.',
        strict_feature_names=FEATURE_NAMES,personality_sensitivity_features=TRAIT_NAMES,
        context_feature_names=CONTROL_NAMES+DEGREES)
    for sign in ['positive','negative']:
        rs=[r for r in retrieval if r['sign']==sign]
        # Equal weight per pair, not per reciprocal direction.
        gp=defaultdict(list)
        for r in rs: gp[tuple(sorted((r['actor'],r['target'])))].append(r)
        results['retrieval'][sign]=dict(pairs=len(gp),directions=len(rs),
            mean_percentile=float(np.mean([np.mean([r['percentile'] for r in group]) for group in gp.values()])),
            profile_mean_percentile=float(np.mean([np.mean([r['profile_percentile'] for r in group]) for group in gp.values()])),
            random_expected_percentile=.5)
    write_ndjson(OUT/'anchor_events.ndjson',events);write_json(OUT/'anchor_cases.json',cases)
    write_ndjson(OUT/'heldout_sign_predictions.ndjson',predictions)
    write_ndjson(OUT/'heldout_members_predictions.ndjson',member_disjoint)
    write_ndjson(OUT/'heldout_retrieval.ndjson',retrieval);write_json(OUT/'fold_audit.json',audit)
    write_json(OUT/'fitted_models.json',models);write_ndjson(OUT/'relationships.ndjson',rows)
    write_json(OUT/'results.json',results)
    after={str(p.relative_to(ROOT)):digest(p) for p in inputs}
    if before!=after: raise RuntimeError('Input changed during run')
    write_json(OUT/'manifest.json',dict(seed=SEED,inputs=before,inputs_unchanged=True,
        sources_reviewed_on=CUTOFF,code={str(p.relative_to(ROOT)):digest(p) for p in sorted(HERE.glob('*.py'))},
        output_hashes={n:digest(OUT/n) for n in ['anchor_events.ndjson','anchor_cases.json',
            'heldout_sign_predictions.ndjson','heldout_members_predictions.ndjson','heldout_retrieval.ndjson',
            'fold_audit.json','fitted_models.json','relationships.ndjson','results.json']}))
    print(json.dumps(results,indent=2),flush=True)


if __name__=='__main__': main()
