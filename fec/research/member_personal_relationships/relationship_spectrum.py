"""Graded, coexisting affinity and tension evidence; no binary edge assignment."""
from collections import defaultdict,Counter
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from .data import ROOT,read_json,write_ndjson,digest
from .run_history import read_rows
from .regression import clean_json,save
from .original_work_context import OUT,INPUT
from .freeze_v5 import verify_lock

AFFINITY={1:'contextual_personal_regard',2:'specific_personal_friendship_declaration',
          3:'specific_personal_bond_or_support_account',4:'repeated_independent_personal_bond_accounts'}
TENSION={1:'isolated_personal_jab',2:'clear_personal_attack_or_avoidance',
         3:'escalating_or_severe_personal_incident',4:'repeated_independent_personal_incidents'}

# Manual grading from the existing context reviews. No label, trait score, party,
# geography, absence of cooperation, or fitted probability determines a grade.
ANCHOR_GRADES={
 '90f03416cc5a4bbf3632':(3,None,'specific_condolence_account'),
 '90cd69ba983466502e47':(2,None,'senate_ceremony_with_specific_family_affection'),
 'df929387644162fa212f':(1,None,'floor_declaration_without_separate_personal_account'),
 '5c41003a37ab9ecc9441':(1,None,'family_memorial_dyad_inference_limited'),
 'anchor-britt_fetterman_nbc_202604-0':(3,None,'personal_trust_and_family_conversations'),
 'anchor-britt_fetterman_nbc_202604-1':(3,None,'hospital_support_account'),
 'anchor-britt_louisville_20240402-0':(2,None,'public_bipartisanship_speech_specific_friend_declaration'),
 'anchor-britt_louisville_20240402-1':(2,None,'public_bipartisanship_speech_specific_friend_declaration'),
 'anchor-britt_louisville_20240402-2':(2,None,'public_bipartisanship_speech_specific_friend_declaration'),
 'anchor-booker_scott_cbs_20160912-0':(2,None,'media_friendship_declaration'),
 'anchor-lee_cruz_radio_20160629-0':(2,None,'best_friend_statement_during_defense'),
 'anchor-collins_murkowski_fox_20181221-0':(3,None,'personal_account_of_friendship_surviving_disagreement'),
 'anchor-coons_lankford_rns_20190130-0':(3,None,'personal_faith_conversation_account'),
 'anchor-cole_mcgovern_20190515-0':(2,None,'specific_superlative_personal_declaration_floor_context'),
 'anchor-mcgovern_cole_20200423-0':(1,None,'floor_work_and_friendship_acknowledgment'),
 'anchor-burchett_cspan_20240517-0':(2,None,'social_relationship_despite_political_opposition'),
 'anchor-burchett_cspan_20240517-1':(2,None,'social_relationship_despite_political_opposition'),
 'anchor-mace_crockett_20250114-0':(None,3,'personal_escalation_same_root_as_hearing_review'),
 'anchor-comer_moskowitz_20231114-0':(None,3,'personal_escalation_same_root_as_hearing_review'),
 'anchor-aoc_cruz_20210128-0':(None,2,'explicit_targeted_avoidance_political_trigger'),
 'anchor-aoc_fetterman_20240517-0':(None,2,'direct_personal_rebuke'),
 'anchor-boebert_omar_202111-0':(None,3,'severe_personal_insinuation_and_call_confrontation'),
 'anchor-boebert_omar_202111-1':(None,2,'target_reports_ending_confrontational_call'),
 'anchor-gosar_aoc_video_20211107-0':(None,3,'severe_personal_targeting_in_violent_imagery'),
 'anchor-vanorden_roy_20240418-0':(None,2,'personal_bully_rebuke_with_political_trigger'),
 'anchor-comer_jeffries_20251120-0':(None,2,'authored_character_accusation_political_trigger'),
 'anchor-comer_jeffries_20251120-1':(None,None,'reported_reverse_accusation_needs_independent_attribution'),
 'anchor-cruz_mcconnell_20150724-0':(None,2,'personal_accusation_about_legislative_promise_not_enduring_dislike'),
 'history-rollcall_civility_20171204-0':(2,None,'prompted_media_specific_friendship_declaration'),
 'history-rollcall_civility_20171204-1':(2,None,'prompted_media_close_friend_declaration'),
 'history-rollcall_civility_20171204-2':(1,None,'prompted_friend_nomination'),
 'history-rollcall_civility_20171204-3':(1,None,'prompted_friend_nomination_and_softball'),
 'history-rollcall_civility_20171204-4':(1,None,'prompted_friend_nomination'),
 'history-rollcall_civility_20171204-5':(1,None,'enjoyable_collaboration_and_possible_visits'),
 'history-rollcall_civility_20171204-6':(1,None,'enjoyable_collaboration'),
 'history-rollcall_civility_20171204-7':(1,None,'prompted_personal_approval'),
 'history-rollcall_civility_20171204-8':(1,None,'prompted_friend_nomination'),
 'history-sanders_warren_20191012-0':(2,None,'decades_long_friendship_declaration_with_disagreement'),
 'history-sanders_warren_20190728-0':(1,None,'friendship_and_work_appreciation'),
 'history-houlahan_bacon_ndaa_20241211-0':(None,None,'floor_work_acknowledgment_courtesy_compatible'),
 'history-durbin_grassley_20211202-0':(None,None,'senate_floor_courtesy_compatible_even_if_called_sincere'),
 'history-durbin_duckworth_20240227-0':(3,None,'specific_private_family_news_trust_account'),
 'history-roy_massie_20240925-0':(1,None,'public_friend_declaration_during_disagreement'),
 'history-omar_aoc_personal_defense_20200723-0':(1,None,'personal_defense_and_family_reference'),
}


def context_grade(r):
    """Courteous warmth stays observed without manufacturing personal closeness."""
    if r['id']=='new_review_44692':
        return None,None,'senate_floor_courtesy_and_coalition_building_not_separated'
    if r['id']=='new_review_60458':
        return 2,None,'specific_support_call_beyond_salutation_but_shared_public_crisis'
    if r['id']=='review_215949':return 3,None,'specific_bereavement_support_and_personal_friendship'
    if r['id']=='review_65329':return 1,None,'personal_regard_in_institutional_tribute'
    if r['decision']=='documented_personal_escalation':return None,3,'context_reviewed_escalation'
    if r['decision']=='personal_jab':return None,1,'isolated_jab_not_sustained_dyadic_conflict'
    return None,None,'courtesy_or_unresolved_or_no_personal_evidence_in_segment'


def summarize(events):
    """Independent channels, observed directions, root-episode deduplication."""
    grouped=defaultdict(list)
    for e in events:grouped[(e['actor'],e['target'],e['episode_id'])].append(e)
    dedup=[]
    for key,rows in grouped.items():
        row=dict(rows[0]);row['source_ids']=[x['id'] for x in rows]
        for channel in ('affinity','tension'):
            values=[x[channel+'_grade'] for x in rows if x[channel+'_grade'] is not None]
            row[channel+'_grade']=max(values) if values else None
        dedup.append(row)
    result={}
    for channel in ('affinity','tension'):
        selected=[e for e in dedup if e[channel+'_grade'] is not None]
        grade=max((e[channel+'_grade'] for e in selected),default=None)
        required=3 if channel=='affinity' else 2
        independent={e['episode_id'] for e in selected if e[channel+'_grade']>=required}
        if len(independent)>=2:grade=4
        result[channel]=dict(evidence_grade=grade,description=(AFFINITY if channel=='affinity' else TENSION).get(grade,'not_established'),
            independent_support_episodes=len({e['episode_id'] for e in selected}),
            directions=[list(d) for d in sorted({(e['actor'],e['target']) for e in selected})],
            latest_support_date=max((e['date'] for e in selected),default=None))
    result.update(mixed_evidence=all(result[k]['evidence_grade'] is not None for k in ('affinity','tension')),
        observed_episode_count=len({e['episode_id'] for e in dedup}),
        event_ids=[e['id'] for e in events],net_friend_vs_enemy_score=None,
        interpretation='Grades measure reviewed evidence strength/intensity; unknown is not neutral; channels do not cancel; no private-feelings probability')
    return result


def main():
    frozen=verify_lock();context=read_rows(OUT/'exchange_context.ndjson')
    old=read_rows(INPUT/'reviewed_events.ndjson');members=read_json(INPUT/'members.json')
    assignment=read_json(ROOT/'outputs/member_personal_relationships/20260910_frozen_v5/member_assignment.json')
    paths=[Path(__file__),INPUT/'reviewed_events.ndjson',OUT/'exchange_context.ndjson',OUT/'work_matrices.npz']
    before={str(p.relative_to(ROOT)):digest(p) for p in paths};events=[]
    for r in context:
        a,h,why=context_grade(r)
        events.append(dict(id=r['id'],actor=r['actor'],target=r['target'],date=r['date'],episode_id=r['episode_id'],
            affinity_grade=a,tension_grade=h,grading_reason=why,source_urls=r['source_urls'],
            observable_warmth=r['personal_content']=='warmth',
            source_type='context_review',courtesy_conditioning_needed='courtesy' in why or 'tribute' in why,
            note=r['interpretation']))
    for r in old:
        a,h,why=ANCHOR_GRADES[r['evidence_id']]
        events.append(dict(id=r['evidence_id'],actor=r['actor'],target=r['target'],date=r['event_date'],
            episode_id=r.get('episode_id',r['source_family']),affinity_grade=a,tension_grade=h,grading_reason=why,
            source_urls=r.get('source_urls',[]),observable_warmth=r['sign']=='positive',source_type='prior_context_review',
            courtesy_conditioning_needed=any(k in why for k in ('courtesy','ceremony','floor','memorial')),
            note=r.get('review_note',r.get('reason'))))
    # These source families were already identified as the exact same encounter.
    for e in events:
        if e['id']=='anchor-mace_crockett_20250114-0':e['episode_id']='mace_crockett_20250114'
        if e['id']=='anchor-comer_moskowitz_20231114-0':e['episode_id']='comer_moskowitz_20231114'
        assert assignment[e['actor']]['split']==assignment[e['target']]['split']=='development'
    ids=read_json(OUT/'matrix_index.json')['ids'];index={a:i for i,a in enumerate(ids)}
    with np.load(OUT/'work_matrices.npz') as z:w={k:z[k] for k in ['direct_rate','shared','weighted_jaccard','network_proximity']}
    grouped=defaultdict(list)
    for e in events:grouped[tuple(sorted((e['actor'],e['target'])))].append(e)
    profiles=[]
    for (a,b),es in sorted(grouped.items()):
        i,j=index[a],index[b];s=summarize(es)
        profiles.append(dict(pair=[a,b],names=[members[a]['name'],members[b]['name']],**s,
            original_work=dict(shared_bills=w['shared'][i,j],a_to_b_propensity=w['direct_rate'][i,j],
                b_to_a_propensity=w['direct_rate'][j,i],weighted_overlap=w['weighted_jaccard'][i,j],
                network_proximity=w['network_proximity'][i,j]),
            personality_conditioned_excess_warmth=None,
            courtesy_baseline_status='Needs representative other-colleague observations matched on chamber, venue and speech purpose; selected cue samples are not a denominator'))
    write_ndjson(OUT/'graded_events.ndjson',events);write_ndjson(OUT/'relationship_spectrum.ndjson',[clean_json(p) for p in profiles])
    schema=dict(representation='Independent graded affinity and tension, plus continuous original-work measures',
        affinity_scale=AFFINITY,tension_scale=TENSION,unknown=None,
        prohibited_interpretations=['Binary friendship/enmity assignment','1 minus affinity equals tension',
            'logistic probability interpreted as closeness','courtesy means dislike','trait profile proves sincerity'],
        courtesy_controls=['Chamber and actual venue','Speech purpose: yield, acknowledgment, tribute, policy appeal',
            'Speaker-specific use toward other colleagues in comparable settings','Target-specific excess, concrete personal acts and independent reciprocity'],
        courtesy_rule='Senate floor evaluations of a colleague may be courtesy or coalition-building, even when phrased as explicit liking. Retain observed words but do not assign personal closeness without differentiating evidence.',
        timing='Every episode dated; historical support does not automatically describe today; no arbitrary 30-day relationship expiry',
        validation='Existing binary regression is a legacy sign diagnostic only. Graded predictions require independently coded graded outcomes and separate development validation before a new frozen evaluation.',
        personality_rule='Personality may condition measured speaker-specific warmth after a comparable exposure baseline exists; no fixed low-A/E sincerity multiplier')
    save(OUT/'spectrum_schema.json',schema)
    lines=['# Relationship spectrum with courtesy controls','',
      'Affinity and interpersonal tension are separate graded dimensions. A pair can show either, both, or insufficient evidence. Original-cooperation propensities remain continuous. A blank/unknown channel is not neutral and does not imply the opposite feeling. These are evidence grades, not calibrated strengths of private emotions.','',
      '**Senate courtesy correction:** Durbin’s liking/respect language toward Tim Scott is retained as observed warmth, but personal closeness is unestablished from that floor exchange. The same scrutiny is applied to Durbin’s floor friendship language toward Grassley. Explicit claims of sincerity are not self-validating. Personal support, private-life accounts or independent reciprocity can provide additional evidence beyond the customary language.','',
      'A speaker baseline must compare other-colleague language in the same chamber, venue and speech purpose. The selected reviews cannot estimate that baseline. Personality-conditioned excess warmth therefore remains missing; low agreeableness or extraversion does not automatically convert courtesy into sincerity.','',
      '| Pair | Affinity evidence (1–4) | Tension evidence (1–4) | Shared original bills | Latest affinity / tension evidence |','|---|---|---|---:|---|']
    for p in profiles:
        a=p['affinity'];h=p['tension']
        def label(v):return 'unestablished' if v['evidence_grade'] is None else f"{v['evidence_grade']} — {v['description'].replace('_',' ')}"
        lines.append(f"| {' / '.join(p['names'])} | {label(a)} | {label(h)} | {p['original_work']['shared_bills']:.0f} | {a['latest_support_date'] or '—'} / {h['latest_support_date'] or '—'} |")
    lines+=['','Affinity: 1 contextual personal regard; 2 a specific friendship declaration; 3 a concrete personal bond/support account; 4 independently repeated concrete accounts. Tension: 1 isolated jab; 2 clear personal attack/avoidance; 3 escalating or severe personal incident; 4 independently repeated incidents. These are ordered categories, not equally spaced units. Grades are assigned from reviewed evidence, never from ideology, geography or a lack of original cosponsorship.','',
      'Public institutional context remains relevant at every grade. A recalled past incident is not a second independently verified episode, duplicate broadcasts do not create repetition, and observed direction is preserved. The dataset includes no extrapolated reverse emotions.','',
      'The completed seven regressions still evaluate the old positive-versus-negative labels for comparability. Their probabilities are not used anywhere in this spectrum. Independent graded annotations are required to test prediction of closeness and tension; that accuracy has not yet been measured. The prior frozen test and its labels remain untouched.','']
    (OUT/'SPECTRUM.md').write_text('\n'.join(lines),encoding='utf-8')
    assert all(digest(ROOT/p)==h for p,h in before.items());assert verify_lock()['freeze_id']==frozen['freeze_id']
    save(OUT/'spectrum_receipt.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),inputs=before,
        event_records=len(events),dyad_profiles=len(profiles),all_development=True,frozen_test_unchanged=True,
        regression_probabilities_used=False,graded_prediction_accuracy=None,
        authority='User requested a spectrum and explicit Senate-courtesy adjustment after the original-work fits'))
    print('Graded spectrum:',len(profiles),'dyads;',len(events),'source records',flush=True)


if __name__=='__main__':main()
