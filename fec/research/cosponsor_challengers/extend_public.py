"""Audit richer raw text, then replace public columns before any model fitting."""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlparse

import numpy as np
import pandas as pd

from audit_data import OUT,ROOT,digest
from build_panel import (FEATURES,PUBLIC,get_bills,get_members,term_at,ordinal,norm,topic_for,
                         csv_rows,frozen_read,RECEIPTS)

POSITIVE=re.compile(r"\b(?:i|we)(?:['’]m|['’]re|\s+am|\s+are)?\s+(?:(?:strongly|fully|proudly|firmly|wholeheartedly)\s+|(?:proud|pleased|happy)\s+to\s+)?(?:support(?:ed)?|endorse(?:d)?|back(?:ed)?|co[ -]?sponsor(?:ed)?|urge\s+(?:the\s+)?(?:house|senate|congress)\s+to\s+pass)\b",re.I)
NEGATIVE=re.compile(r"\b(?:i|we)\s+(?:(?:strongly|firmly)\s+)?(?:oppose(?:d)?|reject(?:ed)?|cannot\s+support|do\s+not\s+support|don['’]t\s+support|will\s+not\s+support|voted?\s+against)\b",re.I)
REF=re.compile(r"\b(H\s*\.?\s*R\s*\.?|S\s*\.)\s*(\d{1,5})\b",re.I)


def direct_stance(sentence,source,last_name):
    if NEGATIVE.search(sentence):
        return -1
    if POSITIVE.search(sentence):
        return 1
    if source=="press" and last_name:
        actor=r"\b"+re.escape(last_name)+r"\s+"
        if re.search(actor+r"(?:strongly\s+)?(?:opposes|rejects)\b",sentence,re.I):
            return -1
        if re.search(actor+r"(?:strongly\s+)?(?:supports|endorses|backs|cosponsors|co-sponsors)\b",sentence,re.I):
            return 1
    return 0


def prepare():
    bills=get_bills()
    members,aliases=get_members()
    bykey={b["key"]:b for b in bills}
    report=collections.Counter()
    titles=collections.defaultdict(list)
    wordfreq=collections.Counter()
    for b in bills:
        for title in b["short_titles"]:
            nt=norm(title)
            if len(nt.split())>=4 and len(nt)>=22:
                titles[b["congress"]].append((nt,b["key"]))
                wordfreq.update(set(nt.split()))
    anchors={}
    for cg,entries in titles.items():
        index=collections.defaultdict(list)
        for title,key in entries:
            token=min(set(title.split()),key=lambda w:(wordfreq[w],-len(w),w))
            index[token].append((title,key))
        anchors[cg]=index
    def match_refs(body,day):
        d=dt.date.fromordinal(day)
        cg=(d.year-1789)//2+1-int(d.year%2==1 and d.month==1 and d.day<3)
        refs=set()
        for match in REF.finditer(body):
            key=f"{cg}:{'hr' if match.group(1).lower().startswith('h') else 's'}:{int(match.group(2))}"
            if key in bykey and bykey[key]["intro"]<=day:
                refs.add(key)
        normalized=norm(body)
        for word in set(normalized.split()):
            for title,key in anchors.get(cg,{}).get(word,[]):
                if title in normalized and bykey[key]["intro"]<=day:
                    refs.add(key)
        return refs
    documents=[]
    # The full hearing store contains parsed speaker turns. The chamber/service test
    # rejects known ambiguous surname resolutions (e.g. a House member in a Senate hearing).
    db=ROOT/"hearings_seq.db"
    before=digest(db)
    con=sqlite3.connect(db.resolve().as_uri()+"?mode=ro",uri=True)
    for package,date_value,payload in con.execute("SELECT package,date,seq FROM hearing_seq ORDER BY date,package"):
        day=ordinal(date_value)
        if not day:
            report["hearing_missing_date"]+=1
            continue
        chamber="Senate" if "shrg" in package else "House" if "hhrg" in package else None
        if chamber is None:
            report["hearing_unknown_chamber"]+=1
            continue
        try:
            turns=json.loads(payload)
        except json.JSONDecodeError:
            report["hearing_invalid_sequence"]+=1
            continue
        report["hearing_packages"]+=1
        for i,turn in enumerate(turns):
            if len(turn)<5 or turn[4]!="M" or not str(turn[3]).strip():
                continue
            mid=aliases.get(norm(turn[0]))
            term=term_at(members[mid],day,chamber) if mid in members else None
            if term is None:
                report["hearing_unresolved_or_wrong_chamber_turns"]+=1
                continue
            if turn[1] in ("D","R") and not term["party"].startswith("Democrat" if turn[1]=="D" else "Republican"):
                report["hearing_party_mismatch_turns"]+=1
                continue
            documents.append(dict(member=mid,day=day,source="hearing",text=str(turn[3]),url=f"https://www.govinfo.gov/app/details/{package}",source_id=f"{package}:{i}"))
    con.close()
    if digest(db)!=before:
        raise RuntimeError("Hearing store changed during read")
    RECEIPTS.append(dict(path=str(db),sha256=before,bytes=db.stat().st_size))
    for r in csv_rows(ROOT/"data/stance/interviews_cu.csv"):
        mid,day=r["bioguide"],ordinal(r["date"])
        if day and mid in members:
            documents.append(dict(member=mid,day=day,source="interview",text=r["text"],url="",source_id=hashlib.sha256(r["text"].encode()).hexdigest()[:20]))
    for r in csv_rows(ROOT/"data/stance/quorum_member_tweets.csv"):
        mid,day=aliases.get(norm(r["member"])),ordinal(r["dt"])
        if not day or mid not in members:
            report["social_missing_identity_or_date"]+=1
            continue
        body=r["Content"]
        if r.get("is_rt")=="1" or re.match(r"\s*(?:RT\s+@|Rep\.|Sen\.)",body,re.I):
            report["social_retweet_or_transcript_excluded"]+=1
            continue
        documents.append(dict(member=mid,day=day,source="social",text=body,url=r.get("Source URL",""),source_id=r["Quorum ID"]))
    # Official article headlines establish actor attribution most reliably; full text
    # is used for matching/context, with position extraction confined to first-person
    # statements or a named-actor headline. Full-text quotes from third parties are
    # deliberately not interpreted as the member's position.
    for r in csv_rows(ROOT/"press_stance_final.csv"):
        mid,day=r.get("bioguide"),ordinal(r.get("date"))
        host=(urlparse(r.get("url","")).hostname or "").lower()
        if day and mid in members and (host.endswith(".house.gov") or host.endswith(".senate.gov")):
            documents.append(dict(member=mid,day=day,source="press",text=r["title"],url=r["url"],source_id=r["url"]))
    evidence=[]
    seen=set()
    for doc in documents:
        signature=(doc["member"],doc["day"],norm(doc["text"]))
        if signature in seen:
            report["duplicate_documents"]+=1
            continue
        seen.add(signature)
        refs=match_refs(doc["text"],doc["day"])
        sentences=re.split(r"(?<=[!?;.])\s+(?=[A-Z\"“])",doc["text"])
        topics=set()
        positive_topics,negative_topics=set(),set()
        positive_bills,negative_bills=set(),set()
        matched=[]
        for sentence in sentences:
            topic=topic_for(sentence)
            sr=match_refs(sentence,doc["day"])
            if topic!="other":
                topics.add(topic)
            stance=direct_stance(sentence,doc["source"],members[doc["member"]]["last"])
            if stance:
                if topic!="other":
                    (positive_topics if stance>0 else negative_topics).add(topic)
                # Match a statement to the bill in the same sentence; pronoun-only
                # statements do not inherit every bill mentioned elsewhere.
                if len(sr)==1:
                    (positive_bills if stance>0 else negative_bills).update(sr)
                matched.append(dict(sentence=sentence[:1500],stance=stance,bills=sorted(sr)))
        topics.update(bykey[key]["topic"] for key in refs if bykey[key]["topic"]!="other")
        if not topics and not refs:
            report["no_financial_topic_or_bill_reference"]+=1
            continue
        record=dict(doc,topics=sorted(topics),positive_topics=sorted(positive_topics),negative_topics=sorted(negative_topics),
                    bills=sorted(refs),positive_bills=sorted(positive_bills),negative_bills=sorted(negative_bills),matched_positions=matched,
                    evidence_id=hashlib.sha256(json.dumps(signature).encode()).hexdigest()[:20])
        evidence.append(record)
        report[f"accepted_{doc['source']}"]+=1
        report[f"year_{dt.date.fromordinal(doc['day']).year}"]+=1
        report["explicit_position_documents"]+=bool(matched)
        report["explicit_bill_position_documents"]+=bool(positive_bills or negative_bills)
        report["bill_reference_documents"]+=bool(refs)
    path=OUT/"public_evidence_extended.jsonl"
    with path.open("w",encoding="utf-8") as f:
        for r in evidence:
            f.write(json.dumps(r,ensure_ascii=False)+"\n")
    result=dict(counts=dict(report),sources=RECEIPTS,evidence_sha256=digest(path),script_sha256=digest(__file__),
                limitations=["Retrospectively parsed speaker attribution has a service/chamber/party guard but is not fully manually validated.",
                             "Some source turns and posts are truncated in upstream stores.","Published date is not historical first-observed date.",
                             "Explicit textual mention is not a complete semantic policy-position classifier."])
    (OUT/"public_extended_audit.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result["counts"],indent=2),flush=True)


class Timeline:
    def __init__(self,records):
        # records are (member code, publication ordinal, support, oppose).
        if records:
            a=np.asarray(records,dtype=np.int64)
            packed=a[:,0]*1000000+a[:,1]
            order=np.argsort(packed,kind="stable")
            self.keys=packed[order]
            values=np.column_stack([np.ones(len(a),dtype=np.int64),a[:,2],a[:,3]])[order]
            self.prefix=np.vstack([np.zeros((1,3),dtype=np.int64),np.cumsum(values,axis=0)])
        else:
            self.keys=np.zeros(0,dtype=np.int64)
            self.prefix=np.zeros((1,3),dtype=np.int64)
    def query(self,member,day,lookback=365):
        lower=member.astype(np.int64)*1000000+day-lookback
        upper=member.astype(np.int64)*1000000+day
        return self.prefix[np.searchsorted(self.keys,upper)]-self.prefix[np.searchsorted(self.keys,lower)]


def apply():
    if not (OUT/"panel_receipt.json").exists():
        raise RuntimeError("Base panel is not complete")
    if (OUT/"development_results.json").exists():
        raise RuntimeError("Public feature revision must precede model results")
    ids=json.loads((OUT/"identifiers.json").read_text())
    midcode={mid:i for i,mid in enumerate(ids["members"])}
    records,topics,bills=[],collections.defaultdict(list),collections.defaultdict(list)
    for line in (OUT/"public_evidence_extended.jsonl").open(encoding="utf-8"):
        r=json.loads(line)
        mid=midcode[r["member"]]
        records.append((mid,r["day"],0,0))
        for topic in r["topics"]:
            topics[topic].append((mid,r["day"],int(topic in r["positive_topics"]),int(topic in r["negative_topics"])))
        for bill in r["bills"]:
            bills[bill].append((mid,r["day"],int(bill in r["positive_bills"]),int(bill in r["negative_bills"])))
    overall=Timeline(records)
    topic_index={key:Timeline(rows) for key,rows in topics.items()}
    bill_index={key:Timeline(rows) for key,rows in bills.items()}
    empty=Timeline([])
    bykey={b["key"]:b for b in get_bills()}
    columns=[FEATURES.index(f) for f in PUBLIC]
    receipt=json.loads((OUT/"panel_receipt.json").read_text())
    receipt["public_extension"]={"evidence_sha256":digest(OUT/"public_evidence_extended.jsonl"),"script_sha256":digest(__file__)}
    for cg in (117,118,119):
        meta=pd.read_parquet(OUT/f"meta_{cg}.parquet")
        x=np.memmap(OUT/f"X_{cg}.f32",dtype=np.float32,mode="r+",shape=(len(meta),len(FEATURES)))
        old_sha=digest(OUT/f"X_{cg}.f32")
        values=np.zeros((len(meta),len(PUBLIC)),dtype=np.float32)
        for group,indices in meta.groupby("group",sort=False).indices.items():
            m=meta.iloc[indices]
            member=m.member.to_numpy()
            day=int(m.day.iloc[0])
            key=ids["bills"][int(m.bill.iloc[0])]
            topic=bykey[key]["topic"]
            t=topic_index.get(topic,empty)
            b=bill_index.get(key,empty)
            values[indices,0]=overall.query(member,day)[:,0]
            values[np.ix_(indices,[1,2,3])]=t.query(member,day)
            values[np.ix_(indices,[4,5,6])]=b.query(member,day)
            values[indices,7]=b.query(member,day,30)[:,0]
            values[indices,8]=t.query(member,day,30)[:,0]
        x[:,columns]=np.log1p(values)
        x.flush()
        counts=dict(any_public_rows=int((values[:,0]>0).sum()),topic_or_bill_rows=int(((values[:,1]>0)|(values[:,4]>0)).sum()),
                    explicit_bill_support_rows=int((values[:,5]>0).sum()),explicit_bill_oppose_rows=int((values[:,6]>0).sum()),
                    topic_or_bill_events=int(meta.y.to_numpy()[((values[:,1]>0)|(values[:,4]>0)) & meta.mature.to_numpy().astype(bool)].sum()))
        receipt["splits"][str(cg)]["public_extension"]=counts
        receipt["splits"][str(cg)]["pre_public_extension_x_sha256"]=old_sha
        receipt["splits"][str(cg)]["x_sha256"]=digest(OUT/f"X_{cg}.f32")
        print("EXTENDED",cg,counts,flush=True)
    (OUT/"panel_receipt.json").write_text(json.dumps(receipt,indent=2))


if __name__=="__main__":
    import sys
    prepare() if sys.argv[1]=="prepare" else apply()
