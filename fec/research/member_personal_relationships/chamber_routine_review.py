"""Cue-independent encounter retrieval from the existing development sample."""
from collections import Counter
import hashlib
import sqlite3
from .data import ROOT, read_json, write_ndjson
from .run_history import read_rows
from .regression import save
from .freeze_v5 import verify_lock
from .history_speech import clean, OTHER_SPEAKER
from .chamber_work import chamber_at
from .run_chamber_degrees import OUT, HISTORY, FROZEN


def main():
    lock=verify_lock();members=read_json(HISTORY/'members.json');assignment=read_json(FROZEN/'member_assignment.json')
    pairs=[r for r in read_rows(FROZEN/'sampled_pairs.ndjson') if r['split']=='development']
    assert len(pairs)==180
    connection=sqlite3.connect((ROOT/'social_media.db').as_uri()+'?mode=ro',uri=True)
    connection.execute('PRAGMA query_only=ON');connection.execute('BEGIN')
    audit=[];candidates=[]
    # Target-full-name search is deliberately narrow: misses nicknames and titled
    # surnames. No-match is a retrieval nonresponse, never an absent relationship.
    for pair in pairs:
        assert all(assignment[i]['split']=='development' for i in pair['pair'])
        total=0
        for actor,target in (pair['pair'],pair['pair'][::-1]):
            name=members[target]['name']
            found=connection.execute('SELECT rowid,member,date,source,package,text FROM speeches WHERE member=? AND date<=? AND text LIKE ? ORDER BY date DESC,rowid DESC LIMIT 2',
                (members[actor]['name'],'2026-09-10','%'+name+'%')).fetchall()
            total+=len(found)
            for rid,_,day,source,package,text in found:
                stop=OTHER_SPEAKER.search(text) if source=='INTERVIEW' else None
                attributed=text[:stop.start()] if stop else text
                layer=chamber_at(members,actor,target,day)
                if not layer:continue
                candidates.append(dict(pair_id=pair['pair_id'],pair=pair['pair'],actor=actor,target=target,
                    names=[members[actor]['name'],members[target]['name']],date=day,venue=source,
                    chamber=layer,source_rowid=rid,source_family=f'{source}:{package}:{day}',episode_id=f'{source}:{package}:{day}',
                    source_hash=hashlib.sha256(text.encode()).hexdigest(),full_source_text=text,attributed_text=attributed,
                    coverage_tiers=[assignment[i]['coverage_tier'] for i in (actor,target)],
                    conditional_pair_inclusion_probability=pair['conditional_inclusion_probability'],
                    retrieval_basis='development_probability_sample_then_full_target_name; no warmth/hostility cue filter',
                    retrieval_truncated_to_latest_two_turns_per_direction=True,
                    sampling_basis='selected_routine_review_not_representative_speaker_denominator',
                    review_status='unreviewed',affinity=None,friction=None))
        audit.append(dict(pair_id=pair['pair_id'],returned_turns=total,
                          no_match_is_unknown=True,relationship_label_assigned=False))
    connection.rollback();connection.close()
    write_ndjson(OUT/'routine_encounter_candidates.ndjson',candidates)
    save(OUT/'routine_retrieval_audit.json',dict(queried_development_pairs=len(pairs),
        pairs_with_returned_turns=sum(r['returned_turns']>0 for r in audit),candidate_turns=len(candidates),
        candidates_by_dated_chamber=dict(Counter(r['chamber'] for r in candidates)),pair_results=audit,
        no_heldout_evidence_queried=True,database_read_only=True,
        limitation='Narrow full-name search and latest-two cap cause nonresponse; original pair weights do not correct encounter selection.',
        frozen_test_unchanged=verify_lock()['freeze_id']==lock['freeze_id']))
    print('Routine retrieval:',len(pairs),'development pairs,',len(candidates),'candidate turns',flush=True)


if __name__=='__main__':main()
