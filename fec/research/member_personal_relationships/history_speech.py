"""Speaker-relative rhetoric, with retrieval kept separate from reviewed evidence."""
import hashlib
import json
import re
import sqlite3
from collections import Counter,defaultdict
from .data import ROOT,normalize,read_json,write_json,write_ndjson
from .prepare_history import OUT

WARM=re.compile(r"\b(?:my (?:good |dear |close |best |personal |old |great )?friend|"
    r"friendship|friends? of mine|friends? with|best friends?|closest friends?|close friends?|"
    r"personal friends?|oldest friends?|we(?:'re| are) friends|love (?:him|her))\b",re.I)
HOSTILE=re.compile(r"\b(?:liar|moron|idiot|jerk|bitch|scumbag|coward|bully|"
    r"despise|loathe|hate (?:him|her)|don.t (?:like|trust|respect) (?:him|her)|"
    r"can.t (?:stand|trust)|no respect for|take it outside|lying to me|lied to me)\b",re.I)
PERSONAL=re.compile(r"\b(?:friendship|friend of mine|friends? with|best friend|closest friend|"
    r"close friend|personal friend|oldest friend|family|wife|husband|hospital|dinner|"
    r"breakfast|lunch|roommate|wedding|fishing|vacation)\b",re.I)
OTHER_SPEAKER=re.compile(r"\b[A-Z][A-Z .,'-]{5,65}(?:\([^\n)]{1,70}\))?:\s")


def clean(text):
    return re.sub(r'\s+',' ',normalize(text)).strip()


def name_matcher(members):
    variants={};last=defaultdict(set)
    for a,p in members.items():
        name=clean(p['name']);variants[name]=a;last[name.split()[-1]].add(a)
    # An unqualified 'Justice', 'Young', 'Strong', 'Case', etc. is never an ID.
    for name,ids in last.items():
        if len(ids)==1:
            for title in ['mr','mrs','ms','senator','sen','representative','rep','congressman','congresswoman']:
                variants[title+' '+name]=next(iter(ids))
    # Prefix trie avoids rescanning thousands of 'Mr <surname>' alternatives
    # on every word in long floor speeches.
    trie={}
    for variant in variants:
        node=trie
        for char in variant:node=node.setdefault(char,{})
        node['']=True
    def regex(node):
        parts=[re.escape(c)+regex(child) for c,child in sorted(node.items()) if c]
        body=parts[0] if len(parts)==1 else '(?:'+'|'.join(parts)+')' if parts else ''
        return '(?:'+body+')?' if '' in node and body else body
    pattern=re.compile(r'\b'+regex(trie)+r'\b')
    return variants,pattern


def nearest_cues(text,actor,variants,pattern):
    normal=clean(text)
    mentions=[(m.start(),m.end(),variants[m.group()]) for m in pattern.finditer(normal) if variants[m.group()]!=actor]
    targets={a for _,_,a in mentions};hits=defaultdict(set)
    # All positions use normalized text, preventing offset errors from punctuation.
    for label,regex in [('warm',WARM),('hostile',HOSTILE)]:
        for cue in regex.finditer(normal):
            dist=[(max(0,s-cue.end(),cue.start()-e),a) for s,e,a in mentions]
            if not dist:continue
            near=min(d for d,a in dist)
            closest={a for d,a in dist if d==near}
            if near<=160 and len(closest)==1: hits[next(iter(closest))].add(label)
    return targets,hits


def main():
    members=read_json(OUT/'members.json');names={clean(p['name']):a for a,p in members.items()}
    variants,pattern=name_matcher(members)
    con=sqlite3.connect((ROOT/'social_media.db').as_uri()+'?mode=ro',uri=True)
    con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
    stats=defaultdict(Counter);pair=defaultdict(Counter);episodes=defaultdict(set)
    seen=set();candidates=[];audit=Counter();logical=hashlib.sha256()
    for rid,name,day,source,package,text in con.execute(
        "SELECT rowid,member,date,source,package,text FROM speeches WHERE date<='2026-09-10' ORDER BY rowid"):
        actor=names.get(clean(name))
        if not actor or not text:continue
        audit['source_rows']+=1
        if audit['source_rows']%25000==0:print(f"Speech baseline: {audit['source_rows']:,} rows scanned",flush=True)
        logical.update(json.dumps([rid,name,day,source,package,text],ensure_ascii=False).encode())
        # A common transcript defect is another speaker appended to the attributed
        # turn. Truncate that tail for the usage baseline and preserve the row ID.
        mixed=OTHER_SPEAKER.search(text) if source=='INTERVIEW' else None
        if mixed:
            text=text[:mixed.start()];audit['mixed_voice_tails_trimmed']+=1
        normal=clean(text)
        if not normal.strip():continue
        key=(actor,day,hashlib.sha256(normal.encode()).hexdigest())
        if key in seen:audit['duplicate_turns_removed']+=1;continue
        seen.add(key)
        st=stats[(actor,source)];st['turns']+=1;st['words']+=len(normal.split())
        st['warm_turns']+=int(bool(WARM.search(normal)));st['hostile_turns']+=int(bool(HOSTILE.search(normal)))
        targets,hits=nearest_cues(text,actor,variants,pattern)
        for target in targets:
            pc=pair[(actor,target,source)];pc['mention_turns']+=1
            for label in hits.get(target,set()):pc[label+'_turns']+=1
        if not hits:continue
        for target,labels in sorted(hits.items()):
            family=f'{source}:{package}:{day}'
            for label in labels:episodes[(actor,target,label)].add(family)
            if not PERSONAL.search(text) and 'hostile' not in labels:continue
            # Literal evidence requires manual reading of full turn before labeling.
            pos=next((m.start() for m in pattern.finditer(normal) if variants[m.group()]==target),0)
            candidates.append(dict(source_rowid=rid,actor=actor,target=target,actor_name=members[actor]['name'],
                target_name=members[target]['name'],date=day,source=source,package=package,source_family=family,
                cue_classes=sorted(labels),text=text[max(0,pos-280):pos+650],
                review_status='unreviewed_retrieval_only',mixed_voice_tail_trimmed=bool(mixed)))
    con.rollback();con.close()
    rows=[];all_targets=defaultdict(Counter)
    for (actor,target,source),pc in pair.items():all_targets[(actor,source)].update(pc)
    for (actor,target,source),pc in sorted(pair.items()):
        totals=all_targets[(actor,source)]-pc
        denominator=totals['mention_turns']
        rows.append(dict(actor=actor,target=target,source=source,**pc,
            warm_rate=pc['warm_turns']/pc['mention_turns'],hostile_rate=pc['hostile_turns']/pc['mention_turns'],
            other_member_mentions=denominator,
            other_warm_rate=totals['warm_turns']/denominator if denominator else None,
            other_hostile_rate=totals['hostile_turns']/denominator if denominator else None,
            warm_episodes=len(episodes[(actor,target,'warm')]),hostile_episodes=len(episodes[(actor,target,'hostile')])) )
    write_ndjson(OUT/'speaker_usage.ndjson',[dict(actor=a,source=s,**v) for (a,s),v in sorted(stats.items())])
    write_ndjson(OUT/'pair_rhetoric.ndjson',rows)
    write_ndjson(OUT/'speech_review_queue.ndjson',candidates)
    audit['deduplicated_turns']=len(seen);audit['retrieved_candidates']=len(candidates)
    write_json(OUT/'speech_manifest.json',dict(audit,queried_rows_sha256=logical.hexdigest(),
        baseline='named-member mentions by same speaker and source, excluding focal target',
        identity='full name or unique surname with congressional title; nearest cue within 160 characters',
        qualification='cue counts are retrieval statistics; context-reviewed episodes supply relationship evidence'))
    print(json.dumps(dict(audit)),flush=True)


if __name__=='__main__':main()
