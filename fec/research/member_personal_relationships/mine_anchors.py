"""Retrieve first-person personal language across the existing full dated corpus."""
import hashlib,json,re,sqlite3
from collections import Counter,defaultdict
from pathlib import Path
from .data import ROOT,normalize,read_json,write_json,write_ndjson

OUT=ROOT/"outputs/member_personal_relationships/20260910_anchored"
POS=re.compile(r"\b(?:friendship|friends? of mine|friends? with|best friends?|closest friends?|close friends?|"
               r"personal friends?|oldest friends?|we(?:'re| are) friends|roommates?|love (?:him|her)|"
               r"(?:breakfast|dinner|lunch|vacation|fishing|golf) (?:with|together)|"
               r"(?:he|she) (?:was|is) (?:there|here) for me)\b",re.I)
NEG=re.compile(r"\b(?:liar|lunatic|moron|idiot|jerk|bitch|scumbag|coward|bully|bullies|"
               r"despise|loathe|hate (?:him|her)|don.t (?:like|trust|respect) (?:him|her)|"
               r"can.t (?:stand|trust)|no respect for|take it outside|personal (?:attack|vendetta|grudge)|"
               r"(?:lying|lied) (?:to me|about me))\b",re.I)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    members=read_json(ROOT/"outputs/member_personal_relationships/20260910_pilot/members.json")
    names={normalize(p['name']):a for a,p in members.items()}
    surnames=defaultdict(set)
    for a,p in members.items(): surnames[normalize(p['name']).split()[-1]].add(a)
    variants=dict(names)
    for name,ids in surnames.items():
        if len(ids)==1: variants[name]=next(iter(ids))
    matcher=re.compile(r"\b(?:"+'|'.join(re.escape(x) for x in sorted(variants,key=len,reverse=True))+r")\b")
    con=sqlite3.connect((ROOT/'social_media.db').as_uri()+'?mode=ro',uri=True)
    con.execute('PRAGMA query_only=ON'); con.execute('BEGIN')
    rows=[]; counts=Counter(); seen=set()
    for rid,member,date,source,package,text in con.execute(
        "SELECT rowid,member,date,source,package,text FROM speeches WHERE date>='2019-01-01' AND date<='2026-09-10' ORDER BY rowid"):
        a=names.get(normalize(member))
        if not a or not text: continue
        counts['turns']+=1
        hits=[(h,'negative') for h in NEG.finditer(text)]+[(h,'positive') for h in POS.finditer(text)]
        if not hits: continue
        counts['trigger_turns']+=1
        for hit,sign in hits:
            lo=max(0,hit.start()-380); hi=min(len(text),hit.end()+460)
            excerpt=text[lo:hi]
            targets={variants[t.group()] for t in matcher.finditer(normalize(excerpt))}-{a}
            for b in targets:
                key=(a,b,sign,hashlib.sha256(excerpt.encode()).hexdigest())
                if key in seen: continue
                seen.add(key)
                rows.append(dict(evidence_id=f'db-{rid}-{b}-{hit.start()}',actor=a,target=b,
                    actor_name=member,target_name=members[b]['name'],date=date,source=source,package=package,
                    source_rowid=rid,source_family=f'{source}:{package}:{date}',trigger=hit.group(),
                    candidate_sign=sign,text=excerpt,full_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                    identity_status='candidate_requires_context_review',review_status='unreviewed'))
    con.rollback();con.close()
    write_ndjson(OUT/'mined_candidates.ndjson',rows)
    grouped=defaultdict(list)
    for r in rows: grouped[(r['actor_name'],r['target_name'],r['candidate_sign'])].append(r)
    summary=sorted([dict(actor=a,target=b,sign=s,records=len(rs),episodes=len({r['source_family'] for r in rs}),
                         first=min(r['date'] for r in rs),last=max(r['date'] for r in rs),
                         examples=[r['evidence_id'] for r in sorted(rs,key=lambda r:r['date'],reverse=True)[:3]])
                    for (a,b,s),rs in grouped.items()],key=lambda r:(r['sign'],-r['episodes'],r['actor'],r['target']))
    write_json(OUT/'mining_summary.json',dict(counts,records=len(rows),pairs=len(grouped),negative_pairs=sum(r['sign']=='negative' for r in summary)))
    write_ndjson(OUT/'mined_pairs.ndjson',summary)
    print(json.dumps(dict(counts,records=len(rows),pairs=len(grouped))))
    print(json.dumps([r for r in summary if r['sign']=='negative'][:35],indent=2))


if __name__=='__main__': main()
