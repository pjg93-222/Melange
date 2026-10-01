"""Freeze a coverage-stratified member/pair sample before any new outcome fit.

No fitting, source-model API calls or production mutations occur here. A second
run verifies the lock instead of redrawing a more convenient test set.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
import hashlib
import json
import numpy as np
from .data import ROOT, read_json, write_json, write_ndjson, digest
from .run_history import read_rows
from .regression import finite, normalized_keys, lookup, clean_json, features
from .relative_expression import leadership_tension

HERE = Path(__file__).resolve().parent
INPUT = ROOT/'outputs/member_personal_relationships/20260910_full_history'
OLD = ROOT/'outputs/member_personal_relationships/20260910_regression'
HEARING = ROOT/'outputs/member_personal_relationships/20260910_hearing_pilot'
OUT = ROOT/'outputs/member_personal_relationships/20260910_frozen_v5'
SEED = 20260910
SHARES = {'LL':.30,'LM':.25,'LH':.15,'MM':.10,'MH':.10,'HH':.10}
CONTEXT = ['same_party','same_state','same_chamber','actor_dw1','target_dw1',
           'actor_dw2','target_dw2','ideology_similarity','issue_similarity',
           'co_service_congresses','actor_leader','target_leader','leadership_tension',
           'actor_log_interview_words','target_log_interview_words']
WORK = ['direct_propensity','reverse_direct_propensity','weighted_shared_jaccard','log_shared_bills']
LEVELS = ['actor_E','target_E','actor_A','target_A']
EXPRESSION = ['relative_warmth','relative_hostility','warmth_x_E','warmth_x_A',
              'hostility_x_A','reciprocal_warmth']
MODELS = {'M0_context_work':CONTEXT+WORK,
          'M1_personality':CONTEXT+WORK+LEVELS,
          'M2_expression':CONTEXT+WORK+LEVELS+EXPRESSION,
          'M3_similarity':CONTEXT+WORK+LEVELS+['similarity_E','similarity_A','similarity_O'],
          'M4_network':CONTEXT+WORK+LEVELS+['network_proximity']}


def relative(path):
    return str(Path(path).relative_to(ROOT)).replace('\\','/')


def stable_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
                                     separators=(',',':'),allow_nan=False).encode()).hexdigest()


def feature_communication(communication):
    # Quiet/unrecorded members can have an explicit null exposure object. Keep
    # the old fitted adapter unchanged, while preserving its missing values.
    return {name:dict(row,raw_text=row.get('raw_text') or {},
                      public_exposure=row.get('public_exposure') or {})
            for name,row in communication.items()}


def input_paths():
    return [HERE/'FROZEN_TEST_V5.md', Path(__file__), HERE/'relative_expression.py',
            HERE/'history_speech.py', HERE/'hearing_escalation.py',
            HERE/'regression.py', HERE/'run_history.py', HERE/'data.py',
            ROOT/'communication_style.json', ROOT/'data/stance/big5_gold_anchored.json',
            INPUT/'members.json',INPUT/'traits.json',INPUT/'matrix_index.json',
            INPUT/'work_matrices.npz',INPUT/'reviewed_events.ndjson',
            INPUT/'pair_rhetoric.ndjson',INPUT/'speech_review_queue.ndjson',
            INPUT/'speech_manifest.json',OLD/'cases.json',
            HEARING/'reviewed_cases.ndjson',HEARING/'CODING_PROTOCOL.md']


def balanced_allocation(total, capacities):
    """Equal allocation over nonempty cells, with capacity-aware redistribution."""
    if total < 0 or total > sum(capacities.values()):
        raise ValueError('Insufficient frame capacity; the frozen design cannot silently change')
    result = {key:0 for key in sorted(capacities)}
    while sum(result.values()) < total:
        for key in result:
            if result[key] < capacities[key]:
                result[key] += 1
                if sum(result.values()) == total:
                    break
    return result


def coverage_roster(members, communication):
    thresholds = {}
    for chamber in sorted({m['chamber'] for m in members.values()}):
        values = [lookup(communication,m['name']).get('raw_text',{}).get('interview_words')
                  for m in members.values() if m['chamber']==chamber]
        valid = [v for v in values if finite(v)]
        if not valid:
            raise ValueError('A chamber has no observed coverage for stratification')
        thresholds[chamber] = list(map(float,np.quantile(valid,[1/3,2/3])))
    rows = {}
    for a,m in sorted(members.items()):
        words = lookup(communication,m['name']).get('raw_text',{}).get('interview_words')
        low,high = thresholds[m['chamber']]
        tier = ('unrecorded' if not finite(words) else
                'low' if words <= low else 'medium' if words <= high else 'high')
        rows[a] = dict(bioguide=a,name=m['name'],party=m['party'],chamber=m['chamber'],
                       state=m['state'],interview_words=words,coverage_tier=tier,
                       coverage_bucket={'unrecorded':'L','low':'L','medium':'M','high':'H'}[tier])
    return rows,thresholds


def prior_evidence(members):
    pairs, people, families = set(),set(),set()
    for e in read_rows(INPUT/'reviewed_events.ndjson'):
        a,b=e['actor'],e['target']
        people.update(x for x in (a,b) if x in members)
        if a in members and b in members:
            pairs.add(tuple(sorted((a,b))))
        if e.get('source_family'):
            families.add(e['source_family'])
    for e in read_rows(HEARING/'reviewed_cases.ndjson'):
        a,b=e.get('actor_id'),e.get('target_id')
        people.update(x for x in (a,b) if x in members)
        if a in members and b in members and a!=b:
            pairs.add(tuple(sorted((a,b))))
    return pairs,people,families


def split_members(roster, known_members, rng):
    cells=defaultdict(list)
    for a,r in sorted(roster.items()):
        r['split']='development'
        r['prior_reviewed_member']=a in known_members
        if a not in known_members:
            cells[(r['coverage_bucket'],r['chamber'],r['party'])].append(a)
    for cell,ids in sorted(cells.items()):
        count=int(np.floor(.25*len(ids)+.5))
        for i in rng.permutation(len(ids))[:count]:
            roster[ids[i]]['split']='heldout'
    return roster


def pair_cell(a,b,roster):
    left,right=roster[a],roster[b]
    order={'L':0,'M':1,'H':2}
    bucket=''.join(sorted((left['coverage_bucket'],right['coverage_bucket']),key=order.get))
    party='same' if left['party']==right['party'] else 'different'
    chamber='+'.join(sorted((left['chamber'],right['chamber'])))
    return bucket+'|'+party+'|'+chamber


def draw_sample(roster,excluded_pairs,rng,counts=None):
    counts=counts or {'development':180,'heldout':120}
    frames=defaultdict(list)
    crossing=0
    for a,b in combinations(sorted(roster),2):
        if roster[a]['split'] != roster[b]['split']:
            crossing+=1
            continue
        if (a,b) in excluded_pairs:
            continue
        frames[(roster[a]['split'],pair_cell(a,b,roster))].append((a,b))
    selected,summary=[],[]
    for split,total in counts.items():
        for bucket,share in SHARES.items():
            amount=int(round(total*share))
            cells={cell:len(pairs) for (s,cell),pairs in frames.items()
                   if s==split and cell.split('|')[0]==bucket}
            allocations=balanced_allocation(amount,cells)
            for cell,number in allocations.items():
                frame=frames[(split,cell)];N=len(frame)
                summary.append(dict(split=split,stratum=cell,frame_n=N,sample_n=number,
                                    conditional_inclusion_probability=number/N))
                for ix in rng.permutation(N)[:number]:
                    a,b=frame[ix]
                    selected.append(dict(pair=[a,b],pair_id=a+'__'+b,
                        names=[roster[a]['name'],roster[b]['name']],split=split,stratum=cell,
                        conditional_inclusion_probability=number/N,design_weight=N/number,
                        design_weight_population='eligible split-specific frame conditional on member assignment',
                        same_state=roster[a]['state']==roster[b]['state'],
                        coverage_tiers=[roster[a]['coverage_tier'],roster[b]['coverage_tier']],
                        review_status='unreviewed',affinity=None,antagonism=None))
    return sorted(selected,key=lambda r:(r['split'],r['pair_id'])),summary,crossing


def personality_audit(gold,members,traits):
    thresholds=gold['design']['activation_gates'];results={}
    for trait,data in gold['traits'].items():
        panels={}
        for name,p in data['validation']['panels'].items():
            assoc=(p['n']>=thresholds['minimum_panel_n'] and
                   finite(p['r']) and p['r']>=thresholds['minimum_panel_r'] and
                   p['permutation_p_one_sided']<=thresholds['maximum_one_sided_permutation_p'])
            panels[name]=dict(n=p['n'],r=p['r'],permutation_p=p['permutation_p_one_sided'],
                              association_pass=bool(assoc),
                              discriminant_pass=bool(assoc and p['diagonal_dominant']))
            if bool(data['association_gates'][name]) != bool(assoc):
                raise ValueError('Stored personality activation gate disagrees with its numbers')
        scores=normalized_keys(data['members']);mismatches=[]
        for a,m in members.items():
            expected=lookup(scores,m['name']).get(trait)
            actual=traits[a].get(trait)
            if expected != actual:
                mismatches.append(a)
        if mismatches:
            raise ValueError(f'{trait}: frozen relationship traits differ from validated snapshot: {mismatches[:5]}')
        results[trait]=dict(retain_current_measure=any(p['association_pass'] for p in panels.values()),
            two_panel_discriminant_support=all(p['discriminant_pass'] for p in panels.values()),
            status=data['status'],panels=panels,selected_weights=data['selected_weights'],
            current_roster_observed=int(sum(finite(t.get(trait)) for t in traits.values())),
            current_roster_n=len(members),scores_match_validated_snapshot=True,
            exact_relationship_source_purge_verified=False,
            new_external_validation_performed=False)
    return dict(rule=thresholds,traits=results,measurement_retention_only=True,
                independent_relationship_validity_established=False)


def discovery_queue(roster,excluded_pairs,excluded_families,rng):
    options=defaultdict(dict)
    for r in read_rows(INPUT/'speech_review_queue.ndjson'):
        pair=tuple(sorted((r['actor'],r['target'])))
        if pair in excluded_pairs or r['source_family'] in excluded_families:
            continue
        if any(a not in roster or roster[a]['split']!='development' for a in pair):
            continue
        bucket=pair_cell(*pair,roster).split('|')[0][0]
        options[bucket].setdefault(pair,[]).append(r)
    result=[]
    for bucket in ('L','M','H'):
        pairs=sorted(options[bucket])
        for i in rng.permutation(len(pairs))[:8]:
            pair=pairs[i]
            # Root/source diversity before extra clips from the same episode.
            rows=sorted(options[bucket][pair],key=lambda r:(r['source_family'],r['source_rowid']))
            result.append(dict(pair=list(pair),pair_id='__'.join(pair),coverage_bucket=bucket,
                names=[roster[a]['name'] for a in pair],arm='cue_enriched_development_only',
                design_weight=None,review_status='unreviewed',candidates=rows))
    return result


def sample_summary(sample,roster,cases):
    out={}
    for label,rows in [('development',[r for r in sample if r['split']=='development']),
                       ('heldout',[r for r in sample if r['split']=='heldout']),
                       ('all_new',sample),('legacy_29',cases)]:
        endpoints=[a for r in rows for a in r['pair']]
        people=set(endpoints)
        out[label]=dict(pairs=len(rows),unique_members=len(people),
            endpoint_coverage_buckets=dict(Counter(roster[a]['coverage_bucket'] for a in endpoints)),
            endpoint_coverage_tiers=dict(Counter(roster[a]['coverage_tier'] for a in endpoints)),
            unique_member_coverage_tiers=dict(Counter(roster[a]['coverage_tier'] for a in people)),
            same_party_pairs=sum(roster[r['pair'][0]]['party']==roster[r['pair'][1]]['party'] for r in rows),
            same_state_pairs=sum(roster[r['pair'][0]]['state']==roster[r['pair'][1]]['state'] for r in rows),
            chamber_pairs=dict(Counter('+'.join(sorted(roster[a]['chamber'] for a in r['pair'])) for r in rows)))
    return out


def verify_lock(out=OUT):
    lock=read_json(out/'freeze_manifest.json')
    for section in ('inputs','outputs'):
        for name,h in lock[section].items():
            path=ROOT/name if section=='inputs' else out/name
            if digest(path)!=h:
                raise ValueError(f'Frozen {section} changed: {name}; create a new study version')
    if stable_hash({k:v for k,v in lock.items() if k!='freeze_id'}) != lock['freeze_id']:
        raise ValueError('Freeze manifest integrity mismatch')
    return lock


def main():
    if (OUT/'freeze_manifest.json').exists():
        lock=verify_lock()
        print(json.dumps(dict(status='existing_freeze_verified_no_redraw',freeze_id=lock['freeze_id'])))
        return
    if OUT.exists() and any(OUT.iterdir()):
        raise ValueError('Partial/nonempty output directory requires inspection; refusing overwrite')
    print('Checking validated traits and drawing frozen strata',flush=True)
    inputs={relative(p):digest(p) for p in input_paths()}
    members=read_json(INPUT/'members.json');traits=read_json(INPUT/'traits.json')
    communication=normalized_keys(read_json(ROOT/'communication_style.json')['members'])
    communication_for_features=feature_communication(communication)
    audit=personality_audit(read_json(ROOT/'data/stance/big5_gold_anchored.json'),members,traits)
    roster,thresholds=coverage_roster(members,communication)
    excluded,known,families=prior_evidence(members)
    rng=np.random.default_rng(SEED)
    split_members(roster,known,rng)
    sample,frame,crossing=draw_sample(roster,excluded,rng)
    discovery=discovery_queue(roster,excluded,families,rng)
    cases=read_json(OLD/'cases.json')
    summary=sample_summary(sample,roster,cases)
    index_data=read_json(INPUT/'matrix_index.json');index={a:i for i,a in enumerate(index_data['ids'])}
    with np.load(INPUT/'work_matrices.npz') as archive:
        w={k:archive[k] for k in archive.files}
    feature_rows=[]
    all_pairs={tuple(r['pair']) for r in sample+discovery+cases}
    for a,b in sorted(all_pairs):
        for left,right in ((a,b),(b,a)):
            row=features(left,right,members,traits,index,w,communication_for_features)
            row.update(actor=left,target=right,pair_id='__'.join(sorted((left,right))))
            for prefix,person in (('actor',members[left]),('target',members[right])):
                row[prefix+'_dw1']=person.get('d1');row[prefix+'_dw2']=person.get('d2')
            distance=row.pop('dw1_distance')
            row['ideology_similarity']=float(np.exp(-distance)) if distance is not None else None
            row['leadership_tension']=leadership_tension(row['same_party'],None,None)
            row.update({key:None for key in EXPRESSION})
            row['expression_status']='requires_reviewed_source_separated_interactions'
            row['trait_source_overlap_status']='unresolved_in_existing_aggregate'
            feature_rows.append(clean_json(row))
    rhetoric=defaultdict(list)
    for r in read_rows(INPUT/'pair_rhetoric.ndjson'):
        rhetoric[tuple(sorted((r['actor'],r['target'])))].append(r)
    corpus=[]
    for r in sample:
        existing=rhetoric[tuple(r['pair'])]
        corpus.append(dict(pair_id=r['pair_id'],split=r['split'],
            named_mention_turns=sum(x['mention_turns'] for x in existing),
            raw_warm_cue_turns=sum(x.get('warm_turns',0) for x in existing),
            raw_hostile_cue_turns=sum(x.get('hostile_turns',0) for x in existing),
            attribution_review_required=True,relationship_label=None,
            note='Frozen name/cue retrieval statistics only; zero is not a negative relationship'))
    schema=dict(version=5,
        review_status=['unreviewed','context_reviewed','ambiguous','unavailable'],
        evidence_dimensions={'affinity':['supported','unknown','explicit_counterevidence'],
                             'antagonism':['supported','unknown','explicit_counterevidence']},
        required_provenance=['actor','target','date','venue','episode_id','source_family','source_locator','source_hash'],
        required_review=['speaker_verified','target_verified','quoted_only','content_status',
                         'substantive_warmth','personal_hostility','promptedness','ritual_language',
                         'personal_act','escalation','reciprocity','repair','alternative_explanation'],
        leadership_context=['actor_leadership_alignment','target_challenged_leadership',
                            'independent_dated_source_ids'],
        reviewer_blinding=['model_scores','personality_values','work_scores'],
        unknown_is_not_zero=True,allow_both_dimensions_supported=True)
    spec=dict(seed=SEED,member_holdout_fraction=.25,sample_counts={'development':180,'heldout':120},
        coverage_bucket_shares=SHARES,coverage_thresholds_by_chamber=thresholds,
        membership=dict(roster=len(roster),previously_reviewed_members=len(known),
                        assignment_counts=dict(Counter(r['split'] for r in roster.values()))),
        excluded_reviewed_pairs=[list(p) for p in sorted(excluded)],
        prior_source_families=sorted(families),cross_split_pairs_outside_frame=crossing,
        models=MODELS,penalties=[.03,.1,.3,1.,3.],
        primary_comparisons=[['M1_personality','M0_context_work'],['M2_expression','M1_personality'],
                             ['M3_similarity','M1_personality'],['M4_network','M1_personality']],
        current_personality_retained=True,forced_personality_or_ideology_signs=False,
        test_outcomes_inspected=False,minimum_signed_labels={'development_per_sign':20,'heldout_per_sign':10})
    OUT.mkdir(parents=True,exist_ok=False)
    write_json(OUT/'analysis_spec.json',spec)
    write_json(OUT/'member_assignment.json',roster)
    write_json(OUT/'sampling_frame.json',frame)
    write_ndjson(OUT/'sampled_pairs.ndjson',sample)
    write_json(OUT/'sample_audit.json',summary)
    write_json(OUT/'personality_gate_audit.json',audit)
    write_json(OUT/'annotation_schema.json',schema)
    write_ndjson(OUT/'development_discovery_queue.ndjson',discovery)
    write_ndjson(OUT/'frozen_features.ndjson',feature_rows)
    write_ndjson(OUT/'initial_corpus_coverage.ndjson',corpus)
    (OUT/'FROZEN_PLAN.md').write_text((HERE/'FROZEN_TEST_V5.md').read_text(encoding='utf-8'),encoding='utf-8')
    readiness=dict(status='sample_frozen_annotation_pending',new_probability_sample_labels=0,
        minimum_requirements=spec['minimum_signed_labels'],models_fitted=0,test_outcomes_opened=False,
        regression_accuracy=None,personality_gain_independently_validated=False,
        missing_features=['reviewed speaker-relative expression','independent dated leadership alignment/challenge'],
        production_modified=False)
    write_json(OUT/'readiness.json',readiness)
    lock=dict(version=5,created_utc=datetime.now(timezone.utc).isoformat(),inputs=inputs,
              outputs={p.name:digest(p) for p in sorted(OUT.iterdir()) if p.is_file()})
    lock['freeze_id']=stable_hash(lock)
    write_json(OUT/'freeze_manifest.json',lock)
    verify_lock()
    print(json.dumps(dict(status='frozen',freeze_id=lock['freeze_id'],sample=summary,
          discovery_pairs=len(discovery),personality_gates={t:r['retain_current_measure'] for t,r in audit['traits'].items()})))


if __name__=='__main__':
    main()
