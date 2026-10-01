"""Source-linked candidate ledger; machine candidates are never gold labels."""
import collections
import csv
import datetime as dt
import hashlib
import json
import re
from urllib.parse import urlparse

from common import OLD, OUT, ROOT, digest, log, stamp, write_json
from build_panel import get_bills, get_members, norm, ordinal, term_at
from extend_public import direct_stance, REF

INTENT = re.compile(r"\b(?:i|we)\s+(?:will|plan\s+to|intend\s+to|am\s+going\s+to|are\s+going\s+to)\s+(?:become\s+(?:a\s+)?|join\s+as\s+(?:a\s+)?)?(?:co[ -]?sponsor|support)\b",re.I)
EXISTING = re.compile(r"\b(?:i|we)(?:\s+(?:am|are|have|was|were)|['’](?:m|re|ve))?\s+(?:(?:a|an|proud|original|already|longtime)\s+)*(?:co[ -]?sponsor(?:ed|ing)?|introduced)\b",re.I)
VOTE = re.compile(r"\b(?:i|we)\s+(?:voted|supported.{0,100}(?:on\s+the\s+floor|in\s+(?:rules\s+)?committee))\b",re.I)


def classify(sentence, source, last):
    if INTENT.search(sentence): return "stated_future_intent"
    if EXISTING.search(sentence): return "self_reported_existing_sponsorship"
    if VOTE.search(sentence): return "past_vote_or_committee_action"
    s = direct_stance(sentence,source,last)
    return "support" if s>0 else "oppose" if s<0 else None


def run():
    if (OUT/"public_review_audit.json").exists():
        raise RuntimeError("Review ledger already frozen")
    bills=get_bills();members,_=get_members();bykey={b['key']:b for b in bills}
    titles=collections.defaultdict(list)
    for b in bills:
        for t in b['short_titles']:
            nt=norm(t)
            if len(nt)>=22 and len(nt.split())>=4: titles[b['congress']].append((nt,b['key']))
    anchor=collections.defaultdict(lambda:collections.defaultdict(list))
    freq=collections.Counter(w for entries in titles.values() for t,k in entries for w in set(t.split()))
    for cg,entries in titles.items():
        for t,k in entries: anchor[cg][min(set(t.split()),key=lambda w:(freq[w],-len(w),w))].append((t,k))
    def refs(body,day):
        d=dt.date.fromordinal(day);cg=(d.year-1789)//2+1-int(d.year%2==1 and d.month==1 and d.day<3)
        found=set()
        for m in REF.finditer(body):
            k=f"{cg}:{'hr' if m.group(1).lower().startswith('h') else 's'}:{int(m.group(2))}"
            if k in bykey and bykey[k]['intro']<=day: found.add(k)
        text=norm(body)
        for w in set(text.split()):
            for title,k in anchor[cg].get(w,[]):
                if title in text and bykey[k]['intro']<=day:found.add(k)
        return found
    seen=set();ledger=[];source_counts=collections.Counter();receipts=[]
    def accept(doc):
        mid,day=doc['member'],doc['day']
        if mid not in members:return
        # Strip URLs to avoid treating tracking parameters as statements or duplicates.
        body=re.sub(r"https?://\S+","",doc['text'])
        key=(mid,day,norm(body))
        if key in seen:return
        seen.add(key);source_counts[(doc['source'],dt.date.fromordinal(day).year)]+=1
        for sentence in re.split(r"(?<=[!?;])\s+|(?<=\.)\s+(?=[A-Z\"“])",body):
            kind=classify(sentence,doc['source'],members[mid]['last'])
            if kind is None:continue
            linked=refs(sentence,day)
            for bill in sorted(linked):
                b=bykey[bill];join=b['joins'].get(mid)
                issue=[]
                if len(linked)>1:issue.append('multiple_bill_references')
                if not term_at(members[mid],day,b['chamber']):issue.append('wrong_chamber_or_not_serving')
                if b['sponsor']==mid:issue.append('bill_sponsor')
                if doc['source']=='press' and not re.search(r'\b'+re.escape(members[mid]['last'])+r'\s+(?:supports|opposes|endorses|backs|cosponsors)',sentence,re.I):
                    issue.append('first_person_press_quote_needs_named_actor_review')
                if not b['finance_at_introduction']:issue.append('outside_finance_universe')
                if join is not None and join<=day:issue.append('already_signed_or_same_day')
                if kind in ['past_vote_or_committee_action','self_reported_existing_sponsorship']:issue.append('retrospective_action_not_new_endorsement')
                lead=join-day if join is not None else None
                ledger.append(dict(evidence_id=hashlib.sha256(json.dumps([key,bill,sentence]).encode()).hexdigest()[:24],
                    member=mid,member_name=members[mid]['name'],bill=bill,published=dt.date.fromordinal(day).isoformat(),
                    introduced=b['introduced'],join_date=dt.date.fromordinal(join).isoformat() if join else None,
                    bill_age=day-b['intro'],lead_days=lead,source=doc['source'],source_id=doc.get('source_id',''),
                    source_url=doc.get('url',''),sentence=sentence,body_sha256=hashlib.sha256(body.encode()).hexdigest(),
                    candidate_kind=kind,issues=issue,review_status='unreviewed_machine_candidate',
                    eligible_pre_sign_candidate=(not issue and kind in ['support','oppose','stated_future_intent']),
                    historical_development=b['congress'] in [117,118],observed_utc=stamp()))
    original=OLD/'public_evidence_extended.jsonl'
    receipts.append(dict(path=str(original),sha256=digest(original)))
    for line in original.open(encoding='utf-8'):accept(json.loads(line))
    for path in sorted((ROOT/'outputs').glob('press_refresh_*/press_delta_fulltext.csv')):
        before=digest(path)
        with path.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                day=ordinal(row.get('date_final') or row.get('date'))
                host=(urlparse(row.get('url','')).hostname or '').lower()
                if not day or day>dt.date.today().toordinal() or not (host.endswith('.house.gov') or host.endswith('.senate.gov')):continue
                accept(dict(member=row.get('bioguide'),day=day,source='press',text=row.get('body',''),url=row.get('url',''),source_id=row.get('url','')))
        if digest(path)!=before:raise RuntimeError(f'Input changed: {path}')
        receipts.append(dict(path=str(path),sha256=before))
    out=OUT/'public_position_review.jsonl'
    with out.open('w',encoding='utf-8') as f:
        for row in sorted(ledger,key=lambda r:(not r['eligible_pre_sign_candidate'],not r['historical_development'],r['published'],r['bill'],r['member'])):
            f.write(json.dumps(row,ensure_ascii=False)+'\n')
    counts=collections.Counter(r['candidate_kind'] for r in ledger)
    good=[r for r in ledger if r['eligible_pre_sign_candidate']]
    audit=dict(completed_utc=stamp(),document_counts={f'{s}:{y}':v for (s,y),v in sorted(source_counts.items())},
               candidate_rows=len(ledger),candidate_types=dict(counts),pre_sign_candidates=len(good),
               historical_pre_sign_candidates=sum(r['historical_development'] for r in good),
               issue_counts=dict(collections.Counter(i for r in ledger for i in r['issues'])),
               ledger_sha256=digest(out),sources=receipts,
               note='Candidates require source/actor review. Historical and current-public audit only; no new public-position model is trained from this ledger.')
    write_json(OUT/'public_review_audit.json',audit)
    log(f"Public review: {len(ledger)} candidates, {len(good)} possible pre-sign statements, {audit['historical_pre_sign_candidates']} historical")


if __name__=='__main__':run()
