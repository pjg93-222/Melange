"""Source-linked mechanism descriptions, never reused as outcome predictors."""
from collections import Counter
from datetime import datetime,timezone
import numpy as np
from .data import ROOT,read_json,digest,write_ndjson
from .run_history import read_rows
from .regression import save,clean_json
from .personality_context import pair_similarity,bipartisan_propensity
from .original_work_context import OUT,INPUT
from .freeze_v5 import verify_lock

V5=ROOT/'outputs/member_personal_relationships/20260910_frozen_v5'
HEARING=ROOT/'outputs/member_personal_relationships/20260910_hearing_pilot'

HEARING_CONTEXT={
 'luna_to_goldman_status_escalation':('procedural_attendance_dispute','attendance_challenge','wealth_status_ridicule',None),
 'mace_frost_dishonesty_borderline':('dispute_over_prior_confrontation','allegation_of_threat','ambiguous_dishonesty_rebuttal',None),
 'comer_to_moskowitz_personal_escalation':('financial_accountability_dispute','challenge_to_chairs_financial_consistency','appearance_and_character_insults','actor_chair_target_member'),
 'mace_to_crockett_confrontation':('campaign_messaging_dispute','address_perceived_as_belittling_by_actor','challenge_to_continue_outside',None),
 'comer_to_goldman_status_jab':('financial_accountability_dispute','other_dyads_exchange','third_party_wealth_jab','actor_chair_target_member'),
 'luna_crockett_tone_policing_borderline':('dispute_over_personal_insults','request_to_calm_down','ambiguous_personal_dismissal',None),
 'crockett_mace_child_borderline':('campaign_messaging_dispute','political_messaging_criticism','idiomatic_address_disputed_as_personal',None),
 'frost_mace_rules_objection_control':('committee_rules_dispute','prior_confrontation','procedural_objection',None),
 'raskin_donalds_debate_rules_control':('committee_rules_dispute','motion_structuring_debate','procedural_disagreement',None),
 'raskin_quotes_eyelashes_control':('dispute_over_personal_insults','another_members_insult','quotation_while_defending_target',None),
 'crockett_wrong_comer_target_control':('dispute_over_personal_insults','chair_ruling','addressee_not_insult_target','target_chair_actor_member'),
 'comer_frost_order_control':('committee_rules_dispute','appeal_of_chair_ruling','chair_enforcing_order','actor_chair_target_member'),
}

NEW_REVIEWS={
 60458:dict(context='community_crisis_and_policy_advocacy',trigger='response_to_colleague_remarks',
    act='recalled_personal_support_and_advice',decision='substantive_personal_warmth',
    interpretation='Murphy recalls Bennet calling and offering advice during the Sandy Hook crisis, and appreciates having him as a friend. Specific support is present; shared policy advocacy also motivates the speech. The recalled call is not counted as a second independently verified episode.',
    url='https://www.govinfo.gov/link/crec/167/s/1756',pages='S1747-S1748'),
 44692:dict(context='competing_policing_reform_proposals',trigger='discussion_of_other_partys_bill_lead',
    act='explicit_personal_liking_with_substantive_disagreement',decision='substantive_personal_warmth',
    interpretation='Durbin directly expresses liking and respect for Scott and personal appreciation of Scott\'s experiences, then criticizes the competing proposal. This is stronger than a salutation; coalition-building rhetoric remains a plausible additional motive. The separate Grassley collaboration story is not attributed to Scott.',
    url='https://www.congress.gov/116/crec/2020/06/17/CREC-2020-06-17-senate.pdf',pages='S3028-S3030'),
}


def build_records():
    rows=[]
    for r in read_rows(HEARING/'reviewed_cases.ndjson'):
        if not r.get('current_roster_pair'):continue
        context,trigger,act,role=HEARING_CONTEXT[r['id']]
        rows.append(dict(id=r['id'],actor=r['actor_id'],target=r['target_id'],actor_name=r['actor'],target_name=r['target'],
            date=r['date'],episode_id=r['episode_id'],source_family=r['source_id'],venue='COMMITTEE',
            context=context,precipitating_exchange=trigger,personal_act=act,institutional_role_asymmetry=role,
            leadership_allegiance_challenge=None,decision=r['decision'],personal_content=r['personal_content'],
            reciprocal_exchange='reciprocal_conflict' in r['markers'],mutual_personal_hostility_established=None,
            persistence_after_boundary='persistence_after_boundary' in r['markers'],repair=r.get('repair'),
            interpretation=r['evidence']+' '+r['alternative'],source_urls=[r['source_url']],
            source_hashes=[r['source_sha256']],source_locator=dict(pdf_pages=r['pdf_pages']),
            review_status='single_contextual_review',context_reviewed_before_trait_join=True,
            independently_observed_audio_volume=False,used_in_regression=False))
    seen={}
    for r in read_rows(V5/'development_reviewed_interactions.ndjson'):
        key=(r['actor'],r['target'],r['episode_id'])
        if key in seen:
            seen[key]['source_hashes'].append(r['source_hash'])
            seen[key]['source_locator']['rowids'].append(r['source_rowid']);continue
        act=r['personal_act']
        context=('bereavement_support_and_constitutional_disagreement' if r['source_rowid']==215949 else
            'procedural_disagreement' if r['source_rowid']==45726 else
            'institutional_tribute' if r['source_rowid']==65329 else
            'policy_advocacy_or_work_acknowledgment' if act=='ritual_or_work_courtesy' else 'attribution_or_context_control')
        decision=('substantive_personal_warmth' if r['substantive_warmth'] else
            'contextual_personal_warmth' if act=='contextual_personal_warmth' else
            'ritual_or_work_courtesy' if r['ritual_language'] else 'ambiguous_or_attribution_control')
        row=dict(id='review_'+str(r['source_rowid']),actor=r['actor'],target=r['target'],
            actor_name=r['actor_name'],target_name=r['target_name'],date=r['date'],episode_id=r['episode_id'],
            source_family=r['source_family'],venue=r['venue'],context=context,precipitating_exchange=None,
            personal_act=act,institutional_role_asymmetry=None,leadership_allegiance_challenge=None,
            decision=decision,personal_content='warmth' if r['substantive_warmth'] else 'not_established_for_focal_pair',
            reciprocal_exchange=None,mutual_personal_hostility_established=None,persistence_after_boundary=None,
            repair=r.get('repair'),interpretation=r['alternative_explanation'],source_urls=r['source_urls'],
            source_hashes=[r['source_hash']],source_locator=dict(rowids=[r['source_rowid']],sqlite=r['source_locator']),
            review_status='single_full_attributed_turn_review',context_reviewed_before_trait_join=True,
            independently_observed_audio_volume=False,used_in_regression=False)
        rows.append(row);seen[key]=row
    for r in read_rows(V5/'development_review_packets.ndjson'):
        if r['source_rowid'] not in NEW_REVIEWS:continue
        review=NEW_REVIEWS[r['source_rowid']]
        rows.append(dict(id='new_review_'+str(r['source_rowid']),actor=r['actor'],target=r['target'],
            actor_name=r['actor_name'],target_name=r['target_name'],date=r['date'],episode_id=r['episode_id'],
            source_family=r['source_family'],venue=r['venue'],context=review['context'],precipitating_exchange=review['trigger'],
            personal_act=review['act'],institutional_role_asymmetry=None,leadership_allegiance_challenge=None,
            decision=review['decision'],personal_content='warmth',reciprocal_exchange=None,
            mutual_personal_hostility_established=None,persistence_after_boundary=None,repair=None,
            interpretation=review['interpretation'],source_urls=[review['url']],source_hashes=[r['source_hash']],
            source_locator=dict(rowids=[r['source_rowid']],sqlite=r['source_locator'],printed_pages=review['pages']),
            review_status='single_full_attributed_turn_review_with_external_passage_verification',
            context_reviewed_before_trait_join=True,independently_observed_audio_volume=False,used_in_regression=False))
    return rows


def main():
    frozen=verify_lock()
    if (OUT/'exchange_context.ndjson').exists():raise ValueError('Context audit exists')
    paths=[HEARING/'reviewed_cases.ndjson',V5/'development_reviewed_interactions.ndjson',
           V5/'development_review_packets.ndjson',INPUT/'traits.json',INPUT/'members.json',
           OUT/'work_matrices.npz',__file__]
    from pathlib import Path
    hashes={str(Path(p).relative_to(ROOT)):digest(p) for p in paths}
    assignment=read_json(V5/'member_assignment.json');members=read_json(INPUT/'members.json')
    traits=read_json(INPUT/'traits.json');ids=read_json(OUT/'matrix_index.json')['ids'];index={a:i for i,a in enumerate(ids)}
    with np.load(OUT/'work_matrices.npz') as z:w={k:z[k] for k in z.files}
    rows=build_records()
    for r in rows:
        a,b=r['actor'],r['target'];i,j=index[a],index[b]
        assert assignment[a]['split']==assignment[b]['split']=='development'
        r.update(traits={a:traits[a],b:traits[b]},EAO_similarity=pair_similarity(a,b,traits),
            recorded_same_party=members[a]['party']==members[b]['party'],same_state=members[a]['state']==members[b]['state'],
            ideology_distance=abs(members[a]['d1']-members[b]['d1']) if members[a].get('d1') is not None and members[b].get('d1') is not None else None,
            original_shared_bills=w['shared'][i,j],original_direct_a_to_b=w['direct'][i,j],
            original_direct_b_to_a=w['direct'][j,i],
            bipartisan_endpoints={a:bipartisan_propensity(i,j,ids,members,w),b:bipartisan_propensity(j,i,ids,members,w)},
            traits_and_work_timing='Current retrospective estimates; do not claim pre-event measurement',
            predictive_eligibility='Descriptive only: labeling episode cannot predict its own outcome; other-target and prior-episode exposure baselines required')
    write_ndjson(OUT/'exchange_context.ndjson',[clean_json(r) for r in rows])
    save(OUT/'exchange_context_schema.json',dict(unit='directed dyad within root episode; duplicate broadcasts collapse',
        context='Observed subject or institutional situation, not inferred competitive motive',
        personal_act='Authored, correctly targeted behavior distinguished from quoted/third-party content',
        missing='null means unestablished, never zero hostility or zero warmth',
        roles='Event-time role explicitly supported by source; leadership allegiance remains unmeasured',
        traits='Existing accepted composite profile, attached after contextual coding; not evidence of sincerity',
        work='Original-cosponsorship measures from the same fixed bill snapshot',
        followup='Collect independently sourced, dated personal exchanges and other-colleague baselines in the development strata; code without scores; reserve v5 evaluation'))
    assert all(digest(ROOT/p)==h for p,h in hashes.items())
    assert verify_lock()['freeze_id']==frozen['freeze_id']
    save(OUT/'exchange_context_receipt.json',dict(finished_utc=datetime.now(timezone.utc).isoformat(),inputs=hashes,
        directed_episode_records=len(rows),root_episodes=len({r['episode_id'] for r in rows}),
        decisions=dict(Counter(r['decision'] for r in rows)),new_full_turn_reviews=len(NEW_REVIEWS),
        regression_labels_added=0,frozen_test_unchanged=True,all_members_development=True))
    print('Context audit:',len(rows),'directed episode records',flush=True)


if __name__=='__main__':main()
