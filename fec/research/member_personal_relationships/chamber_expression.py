"""Chamber/venue/purpose matched expression; selected cue counts are not exposure."""
from collections import defaultdict
from .chamber_work import chamber_at
from .relative_expression import relative_contrast


def matched_expression(interactions, assessments, members, traits):
    """Only fully reviewed, systematically collected encounters supply denominators.

    This explicit provenance gate prevents the previous cue-enriched review
    packets from being promoted to a representative speaker baseline.
    """
    rows=[]
    for r in interactions:
        if r.get('review_status')!='context_reviewed' or r.get('sampling_basis')!='systematic_encounter_review':
            continue
        if not r.get('speaker_verified') or not r.get('target_verified') or r.get('quoted_only'):
            continue
        if r.get('content_status')!='resolved' or not r.get('speech_purpose'):
            continue
        if any(type(r.get(k)) is not bool for k in ('substantive_warmth','personal_hostility')):
            continue
        c=chamber_at(members,r['actor'],r['target'],r['date'])
        if c:rows.append(dict(r,chamber=c))
    output=[]
    all_outcome_families={f for a in assessments for f in a['families']}
    for a in assessments:
        c=chamber_at(members,a['actor'],a['target'],a['date'])
        matched=[r for r in rows if r['actor']==a['actor'] and r['date']<a['date'] and
                 r['chamber']==c and r['venue']==a['venue'] and r['speech_purpose']==a['purpose'] and
                 r['source_family'] not in all_outcome_families and r['episode_id'] not in all_outcome_families]
        units={}
        for r in matched:
            key=(r['target'],r['episode_id'])
            u=units.setdefault(key,dict(target=r['target'],warmth=False,hostility=False))
            u['warmth'] |= r['substantive_warmth'];u['hostility'] |= r['personal_hostility']
        target=[v for v in units.values() if v['target']==a['target']]
        other=[v for v in units.values() if v['target']!=a['target']]
        out=dict(id=a['id'],target_encounters=len(target),other_encounters=len(other),
                 status='available' if target and other else 'insufficient_systematic_reviewed_exposure')
        for channel in ('warmth','hostility'):
            v=relative_contrast(len(target),sum(x[channel] for x in target),len(other),sum(x[channel] for x in other))
            out[channel]=v
            for t in ('E','A'):
                value=traits[a['actor']].get(t)
                out[channel+'_x_'+t]=v['contrast']*value if v['contrast'] is not None and value is not None else None
        output.append(out)
    return output
