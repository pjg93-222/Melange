"""Context-reviewed hearing escalation rubric, separate from lexical retrieval.

The rule consumes explicit reviewed facts. It is not an automated classifier of
raw transcripts and this small purposive pilot does not estimate accuracy.
"""
from collections import Counter,defaultdict
import re
import sqlite3
from .data import ROOT,read_json,write_json,write_ndjson,digest,normalize
from .fetch_hearing_pilot import OUT,SOURCES

MARKERS={'reciprocal_conflict','repeated_personal_attacks','persistence_after_boundary','explicit_confrontation'}
PERSONAL_TYPES={'appearance_ridicule','character_insult','intelligence_insult','personal_taunt',
                'personal_confrontational_challenge','wealth_status_ridicule','family_insult'}
RETRIEVAL=re.compile(r'\b(?:smurf|trust fund|fake eyelashes|false eyelashes|bleach blonde|bad built|'
    r'(?:enough |not |lack\w* )intelligen\w*|liar|idiot|moron|shut up|take (?:it|this) outside|'
    r'feelings hurt|out of control|not cute|calm down|making shit up)\b',re.I)


def assess(case):
    if not case.get('eligible_member_pair'):return 'outside_member_pair_scope'
    if case.get('quotation_only'):return 'quoted_or_reported_not_authored'
    if not case.get('target_clear'):return 'attribution_unresolved'
    if case.get('benign_context_confirmed'):return 'benign_context'
    if case.get('personal_content')=='ambiguous':return 'needs_context_review'
    if case.get('personal_content')!='clear':return 'no_personal_attack_in_selected_segment'
    if not PERSONAL_TYPES.intersection(case.get('personal_types',[])):return 'needs_context_review'
    if MARKERS.intersection(case.get('markers',[])):return 'documented_personal_escalation'
    return 'personal_jab'


def pair_patterns(cases):
    groups=defaultdict(list)
    for c in cases:
        if c['decision']=='documented_personal_escalation':
            groups[tuple(sorted((c['actor'],c['target'])))].append(c)
    out=[]
    for pair,rows in sorted(groups.items()):
        # One confrontation plus retellings/clips remains one root episode.
        episodes={c['episode_id'] for c in rows}
        dates={c['date'] for c in rows}
        out.append(dict(pair=list(pair),directions=[list(d) for d in sorted({(r['actor'],r['target']) for r in rows})],
            episode_ids=sorted(episodes),independent_episode_count=len(episodes),dates=sorted(dates),
            repeated_across_dates=len(episodes)>=2 and len(dates)>=2,
            mutually_personal_in_reviewed_episode=any(len({(r['actor'],r['target']) for r in rows if r['episode_id']==e})==2 for e in episodes),
            current_roster_pair=all(c['current_roster_pair'] for c in rows),
            qualification='Dated personal escalation. Repeated incidents support a pattern; no automatic timeless private-dislike label.'))
    return out


def retrieval_queue():
    queue=[]
    for source in SOURCES:
        pages=read_json(OUT/'sources'/(source['id']+'.pages.json'))
        for page in pages:
            # Cleaning is for retrieval only; official original pages stay intact.
            text=re.sub(r'(?<=[a-z])-\s*\n\s*(?=[a-z])','',page['text'])
            text=re.sub(r'\s+',' ',text)
            for m in RETRIEVAL.finditer(text):
                queue.append(dict(source_id=source['id'],date=source['date'],pdf_page=page['pdf_page'],
                    cue=m.group(),context=text[max(0,m.start()-220):m.end()+330],
                    actor=None,target=None,review_status='unreviewed_retrieval_only',
                    qualification='Includes quotations, procedural discussion and repeat readbacks. A hit is not a relationship label.'))
    return queue


def main():
    source={r['id']:r for r in read_json(OUT/'source_manifest.json')}
    reviews=read_json(ROOT/'fec/research/member_personal_relationships/hearing_pilot_reviews.json')
    members=read_json(OUT.parent/'20260910_full_history/members.json')
    names={' '.join(normalize(m['name']).split()):a for a,m in members.items()}
    regression_pairs={tuple(c['pair']) for c in read_json(OUT.parent/'20260910_regression/cases.json')}
    aliases={'Anna Paulina Luna':'Anna Luna'}
    def member_id(name):
        return names.get(' '.join(normalize(name).split())) or names.get(' '.join(normalize(aliases.get(name,name)).split()))
    cases=[]
    for c in reviews['cases']:
        c=dict(c);s=source[c['source_id']]
        if c.get('eligible_member_pair'):
            for name in [c['actor'],c['target']]:
                if not member_id(name) and name not in reviews['historical_member_names_verified_in_meeting_roster']:
                    raise AssertionError('Unresolved congressional identity: '+name)
        c.update(date=s['date'],source_url=s['url'],source_sha256=s['sha256'],
            actor_id=member_id(c['actor']),target_id=member_id(c['target']),
            current_roster_pair=bool(member_id(c['actor']) and member_id(c['target'])),
            decision=assess(c),review_status='single_contextual_review',
            audio_volume_measured=False,video_independently_reviewed=False)
        if c['decision']!=c['expected']:raise AssertionError(c['id'])
        if max(c['pdf_pages'])>s['pdf_pages']:raise AssertionError('Invalid source page')
        c['already_in_regression_anchor_pairs']=bool(c['actor_id'] and c['target_id'] and
            tuple(sorted((c['actor_id'],c['target_id']))) in regression_pairs)
        cases.append(c)
    write_ndjson(OUT/'reviewed_cases.ndjson',cases)
    patterns=pair_patterns(cases);write_json(OUT/'pair_patterns.json',patterns)
    queue=retrieval_queue();write_ndjson(OUT/'retrieval_queue.ndjson',queue)
    cue_reviews=read_json(ROOT/'fec/research/member_personal_relationships/hearing_cue_reviews.json')
    assert len(queue)==cue_reviews['expected_hits']
    assigned={}
    for group in cue_reviews['groups']:
        for i in group['indices']:
            if i in assigned:raise AssertionError('Duplicate cue review')
            assigned[i]={k:v for k,v in group.items() if k!='indices'}
    assert set(assigned)==set(range(len(queue)))
    write_ndjson(OUT/'reviewed_cue_queue.ndjson',[dict(q,cue_id=i,review_status='single_contextual_review',
        **assigned[i]) for i,q in enumerate(queue)])
    con=sqlite3.connect((ROOT/'social_media.db').as_uri()+'?mode=ro',uri=True)
    con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
    count=con.execute("SELECT count(*),count(DISTINCT package),count(DISTINCT member) FROM speeches WHERE source='CHRG'").fetchone()
    coverage={s['date']:con.execute("SELECT count(*) FROM speeches WHERE source='CHRG' AND date=?",(s['date'],)).fetchone()[0] for s in SOURCES}
    con.rollback();con.close()
    write_json(OUT/'results.json',dict(review_units=len(cases),decision_counts=dict(Counter(c['decision'] for c in cases)),
        qualifying_directed_units=sum(c['decision']=='documented_personal_escalation' for c in cases),
        qualifying_pairs=len(patterns),qualifying_root_meetings=len({c['source_id'] for c in cases if c['decision']=='documented_personal_escalation'}),
        current_roster_qualifying_pairs=sum(p['current_roster_pair'] for p in patterns),
        current_roster_one_off_jabs=[c['id'] for c in cases if c['current_roster_pair'] and c['decision']=='personal_jab'],
        retrieval_hits=len(queue),source_pages=sum(s['pdf_pages'] for s in source.values()),
        cue_dispositions=dict(Counter(r['disposition'] for r in assigned.values())),
        new_current_roster_qualifying_cases=[c['id'] for c in cases if c['current_roster_pair'] and
            c['decision']=='documented_personal_escalation' and not c['already_in_regression_anchor_pairs']],
        existing_CHRG_rows=count[0],existing_CHRG_packages=count[1],existing_CHRG_members=count[2],
        existing_CHRG_rows_on_selected_dates=coverage,
        independent_accuracy_estimate=None,inter_rater_reliability=None,
        regression_refit=False,production_graph_updated=False,
        qualification='Feasibility and coding consistency only; selected examples, one contextual reviewer. Earlier regression scores are unchanged.'))
    write_json(OUT/'receipt.json',dict(sources={s['id']:s['sha256'] for s in source.values()},
        source_files_unchanged=all(digest(s['local_path'])==s['sha256'] for s in source.values()),
        code_sha256=digest(__file__),reviews_sha256=digest(ROOT/'fec/research/member_personal_relationships/hearing_pilot_reviews.json'),
        cue_reviews_sha256=digest(ROOT/'fec/research/member_personal_relationships/hearing_cue_reviews.json'),
        visually_inspected_pdf_pages={'comer_moskowitz_20231114':[47],'oversight_markup_20240516':[17,18,25,28],
            'oversight_organization_20250114':[40,41]}))
    print(read_json(OUT/'results.json'))


if __name__=='__main__':main()
