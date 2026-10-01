"""Read-only full-turn retrieval for the frozen development discovery queue."""
from datetime import datetime,timezone
import hashlib
import json
import sqlite3
from .data import ROOT,read_json,write_json,write_ndjson,digest
from .freeze_v5 import OUT,verify_lock
from .run_history import read_rows
from .history_speech import OTHER_SPEAKER,clean


def main():
    lock=verify_lock()
    destination=OUT/'development_review_packets.ndjson'
    receipt=OUT/'development_retrieval_receipt.json'
    if destination.exists():
        if not receipt.exists() or digest(destination)!=read_json(receipt)['packets_sha256']:
            raise ValueError('Existing review packets need inspection; refusing overwrite')
        print('Existing full-turn development packets verified; no repeat acquisition')
        return
    roster=read_json(OUT/'member_assignment.json')
    queue=read_rows(OUT/'development_discovery_queue.ndjson')
    con=sqlite3.connect((ROOT/'social_media.db').as_uri()+'?mode=ro',uri=True)
    con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
    output=[];seen=set();duplicate_count=0
    for pair in queue:
        if any(roster[a]['split']!='development' for a in pair['pair']):
            raise ValueError('Held-out member in development packet')
        for c in pair['candidates']:
            row=con.execute('SELECT member,date,source,package,text FROM speeches WHERE rowid=?',
                            [c['source_rowid']]).fetchone()
            if row is None:
                raise ValueError('Frozen candidate source row unavailable')
            name,date,source,package,text=row
            if (clean(name)!=clean(c['actor_name']) or date!=c['date'] or
                    source!=c['source'] or package!=c['package']):
                raise ValueError('Source row identity/date changed since frozen retrieval')
            split=OTHER_SPEAKER.search(text) if source=='INTERVIEW' else None
            attributed=text[:split.start()] if split else text
            key=(c['actor'],c['target'],date,hashlib.sha256(clean(attributed).encode()).hexdigest())
            if key in seen:
                duplicate_count+=1
                continue
            seen.add(key)
            output.append(dict(pair_id=pair['pair_id'],pair=pair['pair'],names=pair['names'],
                coverage_bucket=pair['coverage_bucket'],actor=c['actor'],target=c['target'],
                actor_name=c['actor_name'],target_name=c['target_name'],date=date,venue=source,
                source_family=c['source_family'],episode_id=c['source_family'],package=package,
                source_rowid=c['source_rowid'],source_locator=f'sqlite:social_media.db#speeches/rowid={c["source_rowid"]}',
                source_hash=hashlib.sha256(text.encode()).hexdigest(),full_source_text=text,
                attributed_text=attributed,mixed_voice_tail_trimmed=bool(split),
                review_status='unreviewed',arm='cue_enriched_development_only',
                model_scores_provided=False,personality_values_provided=False))
    con.rollback();con.close()
    write_ndjson(destination,output)
    write_json(receipt,dict(created_utc=datetime.now(timezone.utc).isoformat(),
        freeze_id=lock['freeze_id'],code_sha256=digest(__file__),packets_sha256=digest(destination),
        pairs=len(queue),source_turns=len(output),duplicate_candidates_removed=duplicate_count,
        test_evidence_retrieved=False,database_read_only=True,
        original_source_verification='Local stored transcript row; external original not reverified by this retrieval'))
    print(json.dumps(dict(pairs=len(queue),source_turns=len(output),duplicate_candidates_removed=duplicate_count)))


if __name__=='__main__':main()
