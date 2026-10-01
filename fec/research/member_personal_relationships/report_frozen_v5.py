"""Publish preparation results and limited development source review, not new accuracy."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from .data import ROOT,read_json,write_json,write_ndjson,digest
from .freeze_v5 import OUT,HERE,verify_lock
from .run_history import read_rows
from .relative_expression import reviewed_expression


def main():
    lock=verify_lock();audit=read_json(OUT/'sample_audit.json')
    trait=read_json(OUT/'personality_gate_audit.json')['traits']
    roster=read_json(OUT/'member_assignment.json')
    packets=read_rows(OUT/'development_review_packets.ndjson')
    source={r['source_rowid']:r for r in packets}
    decisions=read_json(HERE/'v5_development_reviews.json')['decisions']
    reviewed=[];events={};quarantine=[]
    for decision in decisions:
        p=source[decision['source_rowid']]
        if any(roster[a]['split']!='development' for a in p['pair']):
            raise ValueError('Test member cannot enter development source review')
        category=decision['category']
        record={k:p[k] for k in ['actor','target','actor_name','target_name','pair_id','date',
                 'venue','episode_id','source_family','source_locator','source_hash','source_rowid']}
        record.update(review_status='context_reviewed',reviewer='assistant_context_review',
            review_scope='full_attributed_source_turn',speaker_verified=True,
            target_verified=category!='wrong_target',quoted_only=False,content_status='resolved',
            substantive_warmth=category in ['contextual_personal_warmth','substantive_personal_friendship_statement'],
            personal_hostility=False,promptedness='not_independently_resolved',
            ritual_language=category=='ritual_or_work_courtesy',personal_act=category,
            escalation=None,reciprocity='not_inferred',repair=None,
            alternative_explanation=decision['note'],affinity='supported' if category in
                ['contextual_personal_warmth','substantive_personal_friendship_statement'] else 'unknown',
            antagonism='unknown',strict_signed_tie_eligible=category=='substantive_personal_friendship_statement',
            external_source_verified=bool(decision.get('external_verification_url')),
            source_urls=[decision['external_verification_url']] if decision.get('external_verification_url') else [],
            original_source_family=p['source_family'])
        if decision.get('episode_id'):
            record['episode_id']=decision['episode_id']
            # Put both broadcast retellings in one family as well as one episode.
            record['source_family']=decision['episode_id']
        record['venue']=decision.get('venue',record['venue'])
        if category=='wrong_target':
            match=[a for a,r in roster.items() if r['name']==decision['correct_target_name']]
            record.update(correct_target_id=match[0] if len(match)==1 else None,
                          correct_target_name=decision['correct_target_name'])
            quarantine.append(record)
        reviewed.append(record)
        if record['strict_signed_tie_eligible']:
            key=(record['actor'],record['target'],record['episode_id'])
            event=events.setdefault(key,dict(actor=record['actor'],target=record['target'],
                actor_name=record['actor_name'],target_name=record['target_name'],
                pair_id=record['pair_id'],episode_id=record['episode_id'],date=record['date'],
                sign='positive',evidence_level='personal_statement',direction_observed=True,
                independent_episode_count=1,source_rowids=[],source_urls=[],
                arm='cue_enriched_development_only',reviewer='assistant_context_review',
                private_friendship_probability=None))
            event['source_rowids'].append(record['source_rowid'])
            event['source_urls']=sorted(set(event['source_urls']+record['source_urls']))
    write_ndjson(OUT/'development_reviewed_interactions.ndjson',reviewed)
    write_ndjson(OUT/'development_new_events.ndjson',list(events.values()))
    write_ndjson(OUT/'identity_quarantine.ndjson',quarantine)
    # No labeling episode is available as independent expression evidence.
    label_episodes={r['episode_id'] for r in reviewed if r['affinity']=='supported'}
    expression=reviewed_expression(reviewed,{},excluded_episodes=label_episodes)
    write_ndjson(OUT/'development_expression_availability.ndjson',expression)
    counts=Counter(d['category'] for d in decisions)
    existing=read_rows(OUT/'initial_corpus_coverage.ndjson')
    yield_by_split={}
    for split in ['development','heldout']:
        rr=[r for r in existing if r['split']==split]
        yield_by_split[split]=dict(sampled_pairs=len(rr),
            any_named_mentions=sum(r['named_mention_turns']>0 for r in rr),
            any_raw_cues=sum(r['raw_warm_cue_turns']+r['raw_hostile_cue_turns']>0 for r in rr))
    result=dict(freeze_id=lock['freeze_id'],sampled_pairs=300,development_pairs=180,heldout_pairs=120,
        low_or_unrecorded_endpoint_share=.5,legacy_low_endpoint_share=5/58,
        trait_activation_passes=[t for t,r in trait.items() if r['retain_current_measure']],
        strict_two_panel_traits=[t for t,r in trait.items() if r['two_panel_discriminant_support']],
        source_review=dict(discovery_pairs=24,retrieved_turns=len(packets),reviewed_turns=len(reviewed),
            pairs_with_some_review=len({r['pair_id'] for r in reviewed}),pending_turns=len(packets)-len(reviewed),
            category_counts=dict(counts),new_strict_positive_pairs=len(events),new_negative_pairs=0,
            independent_new_positive_episodes=len(events),wrong_target_hits_quarantined=len(quarantine)),
        probability_sample_local_corpus=yield_by_split,
        probability_sample_labels_reviewed=0,models_refitted=0,test_results_opened=False,
        new_accuracy=None,independent_personality_gain=None,
        software_validation_separate_from_relationship_validation=True)
    write_json(OUT/'preparation_results.json',result)
    trait_rows=[]
    for t,r in trait.items():
        support='Two panels, including discriminant checks' if r['two_panel_discriminant_support'] else 'One panel association; narrower support'
        trait_rows.append(f"| {t} | Retained | {support} | {r['current_roster_observed']}/{r['current_roster_n']} |")
    body=f'''# Relationship study v5: frozen sample and implementation results

The next test is frozen. The sample contains **300 new pairs: 180 development and 120 held out**, covering **307 distinct members**. Half of sampled member appearances belong to the low-coverage or unrecorded-coverage group, versus **8.6% in the earlier 29 labeled pairs**. These are review targets, not 300 newly established relationships.

## What changed

- Ideological similarity is an explicit compatibility feature, with endpoint ideology and political/geographic context retained. No fixed negative geography or ideology penalty is applied.
- Same-party leadership tension has a defined interaction between independently documented leadership support and a target's leadership challenge. Missing evidence stays missing; the variable is not guessed from conflict or party membership.
- Personality-conditioned expression now compares reviewed substantive warmth/hostility toward a target with that speaker's behavior toward other members in the same venue. Sparse counts are shrunk toward the speaker baseline. E/A interactions are learned rather than assigned a sincerity multiplier.
- Affinity and antagonism remain separate evidence dimensions; they can coexist. Repeated clips and reverse directions do not manufacture independent episodes.
- The plan, code, inputs, member assignment, pair draw and feature families are hash-locked. Reruns verify the same draw and refuse changed locked files.

## Stratification actually drawn

| Sample | Pairs | Distinct members | Low/unrecorded endpoint share | Same-party pairs |
| --- | ---: | ---: | ---: | ---: |
| Earlier labeled sample | 29 | 42 | 8.6% | 9 |
| New development draw | 180 | 212 | 50.0% | 87 |
| New held-out draw | 120 | 95 | 50.0% | 60 |

The draw includes 100 House/House, 100 Senate/Senate and 100 mixed-chamber pairs. These deliberate allocations differ from population proportions. Every sampled pair carries its exact conditional cell inclusion probability and design weight. The weights apply only to the eligible split-specific frame, not all possible congressional relationships. Only eight sampled pairs share a state, so that subgroup remains thin.

Coverage thresholds are chamber-specific: House low up to 2,243 recorded interview words and medium up to 8,033; Senate low up to 13,993 and medium up to 48,212.33. Nineteen roster members have unrecorded interview coverage. Twelve of them appear in the new sample; their missing coverage is not converted to a personality score. Recorded interview-source coverage can include broadcast proceedings and is only a visibility proxy.

## Personality measures retained

The stored numerical activation gates were recalculated: at least one panel with n>=30, r>=0.20 and one-sided permutation p<=0.10. All five pass that existing rule; this is not a new external validation. Frozen member scores also match the validated snapshot.

| Trait | Decision | Support | Current members with scores |
| --- | --- | --- | ---: |
{chr(10).join(trait_rows)}

Passing a measurement gate does not remove relationship-source overlap. Existing profiles are retained for the retrospective track. Independent-personality-gain claims still require source-separated evidence. E/A are the primary level features; E/A/O similarity and network proximity each get a separate prespecified test. C/N remain available with their narrower support and do not trigger a model search on the held-out set.

## First source review

A separate development discovery queue contains 24 cue-enriched pairs, eight in each lower-endpoint coverage bucket. Full local source turns were retrieved for all 24 pairs: 27 turns. So far, **17 turns covering 16 pairs have been context-reviewed**; ten longer turns remain pending. This arm has no probability-sample design weight and is not a test set.

One new strict personal-friendship declaration was identified: **Jamie Raskin to Tom Cole**, January 12, 2021. Raskin explicitly valued their enduring friendship while thanking Cole for support during family bereavement, then continued their substantive disagreement. Two broadcasts repeat the same exchange and count as **one episode**. The published transcript also identifies the setting as a committee proceeding, although the local archive labeled the broadcast source as INTERVIEW. [Published broadcast transcript](https://transcripts.cnn.com/show/ctw/date/2021-01-12/segment/02).

Hoyer's personal appreciation of Simpson was retained as contextual warmth, with institutional tribute as an alternative explanation. It was not promoted to a strict private-friendship anchor. Routine yields and bill acknowledgments were kept distinct from substantive relationship accounts.

The review quarantined a Rosen-to-Ocasio-Cortez retrieval: Rosen was thanking **Catherine Cortez Masto**. It also prevented personal stories about Bill Posey and Elijah Cummings from being assigned to nearby mentioned colleagues, and rejected an apparent Clyburn-to-Scott hostility cue because the insult was reported speech about someone else. These are manual attribution decisions; the frozen legacy retrieval statistics have not been rewritten or presented as reviewed labels.

## Evaluation status

The frozen probability sample has **zero completed relationship labels** so far. Existing local name retrieval found mentions for 42/180 development pairs and 19/120 held-out pairs; raw warmth/hostility cues occurred for only 2 and 4 pairs respectively. These are automatic coverage diagnostics, not inspected held-out outcomes. The sparsity is now measured, rather than hidden by only selecting famous documented relationships. No-result pairs remain in the draw and remain unknown.

**No new regression accuracy, calibrated probability or independent personality improvement is claimed.** The previous 29 labels and the new discovery evidence are development information. The new test stays unopened while standardized source review and speaker-baseline collection are completed. The signed-tie benchmark has fixed minimum reporting floors of 20 development examples of each sign and 10 held-out examples of each sign; these are not a power calculation. Unknowns cannot be used to meet those floors.

See [the frozen plan](FROZEN_PLAN.md), [sampling audit](sample_audit.json), [trait gates](personality_gate_audit.json), [sampled pair IDs](sampled_pairs.ndjson), [review decisions](development_reviewed_interactions.ndjson) and [freeze manifest](freeze_manifest.json). Software checks and their receipt are reported separately from statistical validation.
'''
    (OUT/'REPORT.md').write_text(body,encoding='utf-8')
    write_json(OUT/'preparation_receipt.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        freeze_id=lock['freeze_id'],report_code_sha256=digest(__file__),
        decisions_sha256=digest(HERE/'v5_development_reviews.json'),
        derived_outputs={p.name:digest(p) for p in [OUT/'REPORT.md',OUT/'preparation_results.json',
            OUT/'development_reviewed_interactions.ndjson',OUT/'development_new_events.ndjson',
            OUT/'identity_quarantine.ndjson',OUT/'development_expression_availability.ndjson']},
        production_profiles_or_graph_changed=False))
    print(result)


if __name__=='__main__':main()
