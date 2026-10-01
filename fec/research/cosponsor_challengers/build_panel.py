"""Build dated member-bill risk sets without modifying production inputs."""
from __future__ import annotations

import collections
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlparse

os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
import numpy as np
import pandas as pd
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from audit_data import OUT, ROOT, date, digest

TOPICS = {
    "credit_union": r"credit union",
    "digital_assets": r"digital asset|cryptocurrenc|blockchain|stablecoin",
    "cannabis": r"cannabis|marijuana|hemp",
    "housing": r"housing|homeless|homeowner|mortgage|renters|homebuyers",
    "payments": r"interchange|payment|debit card|credit card|overdraft",
    "insurance": r"insurance|insurer|flood insurance",
    "securities": r"securit(?:y|ies)|investment adviser|investor|capital market|stock exchange",
    "credit_reporting": r"credit report|credit scor|consumer report",
    "small_business": r"small business|entrepreneur",
    "agriculture": r"agricultur|farm|ranch|crop|food|nutrition|rural|livestock|dairy|commodity",
    "consumer": r"consumer|financial protection|financial literacy|debt collect",
    "banking": r"bank|depository|financial institution|federal reserve|deposit insurance",
    "lending": r"loan|lending|credit access|creditor",
    "taxation": r"tax|internal revenue",
    "other": r"$^",
}
TOPIC_NAMES = list(TOPICS)
BASE = ["log_prior_signs", "prior_sign_rate", "log_affinity", "affinity_rate", "log_degree",
        "member_d1", "member_d2", "sponsor_d1", "sponsor_d2", "distance_d1", "distance_d2",
        "member_ideology_missing", "sponsor_ideology_missing", "same_party", "same_state",
        "senate", "seniority", "sponsor_majority", "finance_referrals"] + ["topic_"+x for x in TOPIC_NAMES]
ENHANCED = ["log_prior_topic_signs", "prior_topic_rate", "prior_topic_share", "analogue_similarity",
            "analogue_available", "signed_analogue", "sponsored_analogue"]
DYNAMIC = ["log_bill_age", "bill_age", "log_prior_bill_joiners", "log_joins_7d", "log_joins_30d",
           "coparty_join_share", "prior_collaborator_share", "days_since_join", "log_actions_30d",
           "log_actions_total", "days_since_action", "already_passed_chamber", "congress_day"]
PUBLIC = ["public_coverage_365d", "public_topic_mentions_365d", "public_topic_support_365d",
          "public_topic_oppose_365d", "public_bill_mentions_365d", "public_bill_support_365d",
          "public_bill_oppose_365d", "public_bill_recent_30d", "public_topic_recent_30d"]
FEATURES = BASE + ENHANCED + DYNAMIC + PUBLIC
CUTOFF = dt.date(2026, 9, 3).toordinal()
AGES = [0, 35, 70, 105, 140, 175]
RECEIPTS = []
META_COLUMNS=["bill","member","group","day","age","mature","y","duration","event","democrat","senate","n_joined","existing_score"]
META_DTYPE=np.dtype([(name,"f4" if name=="existing_score" else "i4") for name in META_COLUMNS])


def ordinal(value):
    parsed = date(value)
    return dt.date.fromisoformat(parsed).toordinal() if parsed else None


def frozen_read(path):
    path = Path(path)
    data = path.read_bytes()
    h = hashlib.sha256(data).hexdigest()
    if digest(path) != h:
        raise RuntimeError(f"Input changed while read: {path}")
    RECEIPTS.append({"path": str(path.resolve()), "sha256": h, "bytes": len(data)})
    return data


def csv_rows(path):
    import io
    return list(csv.DictReader(io.StringIO(frozen_read(path).decode("utf-8-sig"))))


def norm(value):
    s = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def normalize_title(value):
    s = norm(value)
    return re.sub(r"\b(?:of )?(?:19|20)\d\d\b", "", s).strip()


def topic_for(value):
    for key, pattern in TOPICS.items():
        if re.search(pattern, value, re.I):
            return key
    return "other"


def get_bills():
    audit = json.loads((OUT / "data_audit.json").read_text())
    assert digest(OUT / "bills.jsonl") == audit["extracted_bills_sha256"]
    all_bills = []
    for line in (OUT / "bills.jsonl").open(encoding="utf-8"):
        b = json.loads(line)
        b["intro"] = ordinal(b["introduced"])
        b["short_titles"] = [t["text"] for t in b["titles"] if "short" in t["kind"].lower()]
        b["title_text"] = " ".join(t["text"] for t in b["titles"])
        b["topic"] = topic_for(b["title_text"])
        b["topic_idx"] = TOPIC_NAMES.index(b["topic"])
        joins = {}
        for c in b["cosponsors"]:
            day = ordinal(c["date"])
            if day is None:
                raise ValueError(f"missing join date {b['key']}")
            joins[c["member"]] = min(day, joins.get(c["member"], day))
        b["joins"] = joins
        b["action_days"] = sorted({ordinal(a["date"]) for a in b["actions"] if a["date"]})
        b["end_congress"] = dt.date(1789 + 2*b["congress"], 1, 3).toordinal()
        b["enacted"] = min([ordinal(a["date"]) for a in b["actions"]
                            if a["date"] and (a["type"].lower() == "president"
                                and re.search(r"became.*law|signed by president", a["text"], re.I))] or [10**9])
        all_bills.append(b)
    return all_bills


def get_members():
    members, aliases = {}, collections.defaultdict(set)
    base = ROOT / "data/staffer_network/reference/congress-legislators"
    directories = sorted(p for p in base.iterdir() if p.is_dir())
    if len(directories) != 1:
        raise ValueError("Ambiguous legislator reference snapshot")
    for name in ("legislators-current.yaml", "legislators-historical.yaml"):
        rows = yaml.load(frozen_read(directories[0] / name), Loader=yaml.CSafeLoader)
        for r in rows:
            mid = r["id"].get("bioguide")
            if not mid:
                continue
            terms = []
            for t in r.get("terms", []):
                if t["type"] not in ("rep", "sen"):
                    continue
                start, end = ordinal(t["start"]), ordinal(t["end"])
                terms.append({"start": start, "end": end, "chamber": "House" if t["type"] == "rep" else "Senate",
                              "state": t["state"], "party": t.get("party", "Unknown")})
            if not terms or max(t["end"] for t in terms) < ordinal("2019-01-01"):
                continue
            person = r.get("name", {})
            full = person.get("official_full") or (person.get("first", "") + " " + person.get("last", ""))
            members[mid] = {"terms": sorted(terms, key=lambda t: t["start"]), "name": full,
                            "last": person.get("last", ""), "first_start": min(t["start"] for t in terms)}
            for name_value in [full, person.get("first", "") + " " + person.get("last", ""),
                               person.get("nickname", "") + " " + person.get("last", "")]:
                aliases[norm(name_value)].add(mid)
    for r in csv_rows(ROOT / "fec/legislators.csv"):
        aliases[norm(r["full_name"])].add(r["bioguide_id"])
    return members, {k:next(iter(v)) for k,v in aliases.items() if len(v)==1}


def term_at(person, day, chamber):
    matches = [t for t in person["terms"] if t["start"] <= day < t["end"] and t["chamber"] == chamber]
    return max(matches, key=lambda t: t["start"]) if matches else None


def service_end(person, term):
    end = term["end"]
    for t in person["terms"]:
        if t["chamber"] == term["chamber"] and t["start"] <= end+1 and t["end"] > end:
            end = t["end"]
    return end


def label_window(join_day, forecast_day, observation_end):
    if join_day is not None and join_day <= forecast_day:
        raise ValueError("Already signed candidate")
    duration = min(30, observation_end-forecast_day)
    if duration <= 0:
        return None
    event = join_day is not None and forecast_day < join_day <= forecast_day+duration
    return {"mature": duration == 30, "y": int(event),
            "duration": (join_day-forecast_day) if event else duration, "event": int(event)}


def prior_stats(bills, cg):
    counts, affinity, sponsor_totals = collections.Counter(), collections.Counter(), collections.Counter()
    topic_counts, topic_totals = collections.Counter(), collections.Counter()
    chamber_totals, neighbors = collections.Counter(), collections.defaultdict(set)
    for b in bills:
        if b["congress"] != cg:
            continue
        chamber_totals[b["chamber"]] += 1
        topic_totals[(b["chamber"], b["topic"])] += 1
        sponsor_totals[b["sponsor"]] += 1
        for mid, day in b["joins"].items():
            if day >= b["end_congress"]:
                continue
            counts[mid] += 1
            topic_counts[(mid,b["topic"])] += 1
            affinity[(mid,b["sponsor"])] += 1
            neighbors[mid].add(b["sponsor"])
            neighbors[b["sponsor"]].add(mid)
    return dict(counts=counts, affinity=affinity, sponsor_totals=sponsor_totals,
                topic_counts=topic_counts, topic_totals=topic_totals, chamber_totals=chamber_totals, neighbors=neighbors)


def get_ideology():
    data = {}
    for r in csv_rows(ROOT / "votes/HSall_members.csv"):
        cg = int(r["congress"])
        if 116 <= cg <= 118 and r["bioguide_id"] and r["chamber"] in ("House", "Senate"):
            try:
                value = (float(r["nominate_dim1"]), float(r["nominate_dim2"]))
                if all(np.isfinite(value)):
                    data[(cg,r["bioguide_id"])] = value
            except ValueError:
                pass
    return data


def match_analogues(bills):
    matches = {}
    for cg in (117,118,119):
        prior = [b for b in bills if b["congress"]==cg-1]
        target = [b for b in bills if b["congress"]==cg and b["finance_at_introduction"]]
        for chamber in ("House", "Senate"):
            pb = [b for b in prior if b["chamber"]==chamber]
            tb = [b for b in target if b["chamber"]==chamber]
            vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,4), min_df=2, max_features=40000, dtype=np.float32)
            pm = vectorizer.fit_transform([normalize_title(b["title_text"]) for b in pb])
            tm = vectorizer.transform([normalize_title(b["title_text"]) for b in tb])
            short_index = collections.defaultdict(list)
            for i,b in enumerate(pb):
                for t in b["short_titles"]:
                    nt = normalize_title(t)
                    if len(nt.split()) >= 4:
                        short_index[nt].append(i)
            for start in range(0,len(tb),100):
                sim = cosine_similarity(tm[start:start+100], pm)
                for j,b in enumerate(tb[start:start+100]):
                    exact = sorted({i for t in b["short_titles"] for i in short_index.get(normalize_title(t),[])})
                    candidates = [i for i in exact if pb[i]["topic"]==b["topic"]]
                    if candidates:
                        best = max(candidates, key=lambda i:(sim[j,i], pb[i]["key"]))
                        score = float(sim[j,best])
                        method = "same_normalized_short_title"
                    else:
                        best = int(sim[j].argmax())
                        score = float(sim[j,best])
                        method = "introduced_title_cosine"
                    if score >= 0.90 and pb[best]["topic"]==b["topic"]:
                        matches[b["key"]] = {"prior_key":pb[best]["key"], "similarity":score, "method":method}
        print(f"ANALOGUES {cg}: {sum(k.startswith(str(cg)+':') for k in matches)}", flush=True)
    (OUT/"analogue_links.json").write_text(json.dumps(matches,indent=2),encoding="utf-8")
    return matches


SUPPORT = r"(?:support|endorse|cosponsor|co-sponsor|back|urge.{0,30}pass|call.{0,30}pass)"
OPPOSE = r"(?:oppose|reject|vote against|cannot support|do not support|don't support|will not support)"


def explicit_stance(text_value, source, last_name=""):
    """Strict first-person attribution, or named actor in an official press headline."""
    body = text_value.lower()
    actor = r"\b(?:i|we)\b.{0,45}?"
    if source == "press" and last_name:
        actor = rf"(?:\b(?:i|we)\b|\b{re.escape(last_name.lower())}\b).{{0,45}}?"
    if re.search(actor+OPPOSE, body):
        return -1
    if re.search(actor+SUPPORT, body):
        return 1
    return 0


def prepare_public(bills, members, aliases):
    sources, report = [], collections.Counter()
    # Only raw text/date/identity are used, never existing stance labels.
    for r in csv_rows(ROOT / "press_stance_final.csv"):
        day, mid = ordinal(r.get("date")), r.get("bioguide", "")
        if not day or mid not in members:
            report["press_missing_date_or_identity"] += 1
            continue
        host = (urlparse(r.get("url", "")).hostname or "").lower()
        if not (host.endswith(".house.gov") or host.endswith(".senate.gov")):
            report["press_third_party_excluded"] += 1
            continue
        sources.append(dict(member=mid, day=day, source="press", text=r["title"], url=r["url"], input="press_stance_final.csv"))
    for rel, source in [("data/stance/hearings_cu.csv","hearing"),("data/stance/interviews_cu.csv","interview")]:
        for r in csv_rows(ROOT/rel):
            day,mid=ordinal(r.get("date")),r.get("bioguide","")
            if day and mid in members:
                sources.append(dict(member=mid,day=day,source=source,text=r["text"],url="",input=rel))
    for r in csv_rows(ROOT / "data/stance/tweet_stance_final.csv"):
        day, mid = ordinal(r.get("date")), aliases.get(norm(r.get("member", "")))
        if not day or not mid:
            report["tweet_missing_identity_or_date"] += 1
            continue
        if re.match(r"\s*(?:RT\s+@|Rep\.|Sen\.)",r.get("text", ""),re.I):
            report["tweet_retweet_or_transcript_excluded"] += 1
            continue
        sources.append(dict(member=mid,day=day,source="tweet",text=r["text"],url="",input="data/stance/tweet_stance_final.csv",source_id=r.get("quorum_id")))
    bill_by_key={b["key"]:b for b in bills}
    titles=collections.defaultdict(list)
    for b in bills:
        for title in b["short_titles"]:
            nt=norm(title)
            if len(nt.split())>=4 and len(nt)>=22:
                titles[b["congress"]].append((nt,b["key"]))
    indexed=collections.defaultdict(list)
    seen=set()
    source_path=OUT/"public_evidence.jsonl"
    with source_path.open("w",encoding="utf-8") as f:
        for s in sources:
            body=s["text"]
            signature=(s["member"],s["day"],norm(body))
            if signature in seen:
                continue
            seen.add(signature)
            daydate=dt.date.fromordinal(s["day"])
            cg=(daydate.year-1789)//2+1
            if daydate.year%2 and (daydate.month,daydate.day)<(1,3):
                cg-=1
            refs=set()
            for match in re.finditer(r"\b(H\s*\.?\s*R\s*\.?|S\s*\.)\s*(\d{1,5})\b",body,re.I):
                kind="hr" if match.group(1).upper().startswith("H") else "s"
                key=f"{cg}:{kind}:{int(match.group(2))}"
                if key in bill_by_key and bill_by_key[key]["intro"]<=s["day"]:
                    refs.add(key)
            normalized=norm(body)
            for title,key in titles.get(cg,[]):
                if title in normalized and bill_by_key[key]["intro"]<=s["day"]:
                    refs.add(key)
            stance=explicit_stance(body,s["source"],members[s["member"]]["last"])
            # A statement mentioning multiple bills has no unambiguous bill-level stance.
            s.update(topic=topic_for(body),stance=stance,bills=sorted(refs),bill_stance=stance if len(refs)==1 else 0)
            s["evidence_id"]=hashlib.sha256(json.dumps(signature).encode()).hexdigest()[:20]
            indexed[s["member"]].append(s)
            f.write(json.dumps(s,ensure_ascii=False)+"\n")
            report[f"accepted_{s['source']}"]+=1
            report[f"accepted_year_{daydate.year}"]+=1
            report["with_explicit_stance"]+=bool(stance)
            report["with_bill_reference"]+=bool(refs)
            report["explicit_bill_stance"]+=bool(s["bill_stance"])
    for records in indexed.values():
        records.sort(key=lambda s:s["day"])
    (OUT/"public_extraction_audit.json").write_text(json.dumps(dict(report),indent=2),encoding="utf-8")
    print("PUBLIC",dict(report),flush=True)
    return indexed


def public_features(evidence, day, bill_key, topic):
    rows=[s for s in evidence if day-365<=s["day"]<day]
    topic_rows=[s for s in rows if s["topic"]==topic and topic!="other"]
    bill_rows=[s for s in rows if bill_key in s["bills"]]
    values=[len(rows),len(topic_rows),sum(s["stance"]>0 for s in topic_rows),sum(s["stance"]<0 for s in topic_rows),
            len(bill_rows),sum(s["bill_stance"]>0 for s in bill_rows),sum(s["bill_stance"]<0 for s in bill_rows),
            sum(s["day"]>=day-30 for s in bill_rows),sum(s["day"]>=day-30 for s in topic_rows)]
    return np.log1p(values)


def existing_scores():
    path=Path(os.environ["LOCALAPPDATA"])/"Melange/lda_rebuild/derived/cosponsor_sc/cosponsor_scores.csv"
    before=digest(path)
    frame=pd.read_csv(path,usecols=["candidate_configuration","congress","bill","member","predicted_probability"])
    frame=frame[frame.candidate_configuration.eq("same_chamber_only") & frame.bill.str.match(r"^(HR|S) ")]
    d={}
    for cg,bill,mid,p in frame[["congress","bill","member","predicted_probability"]].itertuples(index=False,name=None):
        kind,number=bill.split()
        d[(f"{cg}:{kind.lower()}:{int(number)}",mid)]=p
    if digest(path)!=before:
        raise RuntimeError("Production scores moved during snapshot")
    RECEIPTS.append({"path":str(path),"sha256":before,"bytes":path.stat().st_size})
    return d


def build():
    if (OUT/"panel_receipt.json").exists():
        raise RuntimeError("Panel already frozen")
    bills=get_bills()
    members,aliases=get_members()
    mids=sorted(members)
    mid_codes={mid:i for i,mid in enumerate(mids)}
    ideology=get_ideology()
    analogues=match_analogues(bills)
    public=prepare_public(bills,members,aliases)
    old_scores=existing_scores()
    by_key={b["key"]:b for b in bills}
    bill_keys=sorted(b["key"] for b in bills if b["congress"]>=117 and b["finance_at_introduction"])
    bill_codes={key:i for i,key in enumerate(bill_keys)}
    splits={}
    for cg in (117,118,119):
        pri=prior_stats(bills,cg-1)
        selected=[by_key[k] for k in bill_keys if k.startswith(str(cg)+":")]
        maxrows=len(selected)*len(mids)*len(AGES)
        # Raw float32 files can be streamed and memory-mapped by the model runner.
        x_path=OUT/f"X_{cg}.f32"
        metadata=[]
        counts=collections.Counter()
        meta_raw_path=OUT/f"meta_{cg}.raw"
        with x_path.open("wb") as xf,meta_raw_path.open("wb") as mf:
            for bi,b in enumerate(selected):
                sponsor=members.get(b["sponsor"])
                if not sponsor:
                    counts["missing_sponsor_identity_bills"]+=1
                    continue
                an=analogues.get(b["key"])
                prior_bill=by_key[an["prior_key"]] if an else None
                for age in AGES:
                    day=b["intro"]+age
                    if day>=min(CUTOFF,b["end_congress"]-1,b["enacted"]):
                        continue
                    st=term_at(sponsor,day,b["chamber"]) or term_at(sponsor,b["intro"],b["chamber"])
                    if not st:
                        continue
                    joined={mid:d for mid,d in b["joins"].items() if d<day}
                    join_dates=list(joined.values())
                    actions=[a for a in b["actions"] if a["date"] and ordinal(a["date"])<day]
                    action_days=[ordinal(a["date"]) for a in actions]
                    joins7=sum(day-7<=d<day for d in join_dates)
                    joins30=sum(day-30<=d<day for d in join_dates)
                    joined_parties=collections.Counter()
                    for jm in joined:
                        jt=term_at(members[jm],day,b["chamber"]) if jm in members else None
                        if jt:
                            joined_parties[jt["party"]]+=1
                    group=bill_codes[b["key"]]*len(AGES)+AGES.index(age)
                    rows=[]
                    for mid in mids:
                        if mid==b["sponsor"] or b["joins"].get(mid,10**9)<=day:
                            continue
                        person=members[mid]
                        term=term_at(person,day,b["chamber"])
                        if not term:
                            continue
                        observation_end=min(CUTOFF,b["end_congress"]-1,service_end(person,term)-1)
                        label=label_window(b["joins"].get(mid),day,observation_end)
                        if not label:
                            continue
                        m_ideo=ideology.get((cg-1,mid))
                        s_ideo=ideology.get((cg-1,b["sponsor"]))
                        mi=m_ideo or (0,0)
                        si=s_ideo or (0,0)
                        affinity=pri["affinity"][(mid,b["sponsor"])]
                        propensity=pri["counts"][mid]/max(1,pri["chamber_totals"][b["chamber"]])
                        topic_count=pri["topic_counts"][(mid,b["topic"])]
                        num_topics=pri["topic_totals"][(b["chamber"],b["topic"])]
                        majority="Democrat" if cg==117 or (cg==118 and b["chamber"]=="Senate") else "Republican"
                        values=[np.log1p(pri["counts"][mid]),propensity,np.log1p(affinity),
                                (affinity+0.3)/(pri["sponsor_totals"][b["sponsor"]]+10),np.log1p(len(pri["neighbors"][mid])),
                                *mi,*si,abs(mi[0]-si[0]) if m_ideo and s_ideo else 0,abs(mi[1]-si[1]) if m_ideo and s_ideo else 0,
                                int(m_ideo is None),int(s_ideo is None),int(term["party"]==st["party"]),int(term["state"]==st["state"]),
                                int(b["chamber"]=="Senate"),(day-person["first_start"])/365.25,int(st["party"]==majority),
                                len({c["code"] for c in b["committees"] if c["date"]==b["introduced"] and c["activity"].lower()=="referred to"})]
                        values += [int(b["topic"]==topic) for topic in TOPIC_NAMES]
                        values += [np.log1p(topic_count),(topic_count+10*propensity)/(num_topics+10),topic_count/max(1,pri["counts"][mid]),
                                   an["similarity"] if an else 0,int(an is not None),int(prior_bill is not None and mid in prior_bill["joins"]),
                                   int(prior_bill is not None and mid==prior_bill["sponsor"])]
                        values += [np.log1p(age),age,np.log1p(len(joined)),np.log1p(joins7),np.log1p(joins30),
                                   joined_parties[term["party"]]/max(1,len(joined)),len(pri["neighbors"][mid]&joined.keys())/max(1,len(joined)),
                                   min(365,day-max(join_dates)) if join_dates else 365,np.log1p(sum(d>=day-30 for d in action_days)),
                                   np.log1p(len(action_days)),min(365,day-max(action_days)) if action_days else 365,
                                   int(any(a["type"].lower()=="passage" for a in actions)),day-dt.date(1789+2*(cg-1),1,3).toordinal()]
                        values += list(public_features(public.get(mid,[]),day,b["key"],b["topic"]))
                        assert len(values)==len(FEATURES)
                        rows.append(values)
                        metadata.append((bill_codes[b["key"]],mid_codes[mid],group,day,age,label["mature"],label["y"],label["duration"],
                                         label["event"],int(term["party"]=="Democrat"),int(b["chamber"]=="Senate"),len(joined),
                                         old_scores.get((b["key"],mid),np.nan)))
                        counts["rows"]+=1
                        counts["mature_rows"]+=label["mature"]
                        counts["mature_events"]+=label["y"] if label["mature"] else 0
                        counts["public_topic_or_bill_rows"]+=bool(values[-8] or values[-5])
                    if rows:
                        np.asarray(rows,dtype=np.float32).tofile(xf)
                        np.asarray(metadata,dtype=META_DTYPE).tofile(mf)
                        metadata.clear()
                if (bi+1)%400==0:
                    print(f"PANEL {cg}: {bi+1}/{len(selected)} bills, {counts['rows']:,} rows",flush=True)
        raw_meta=np.memmap(meta_raw_path,dtype=META_DTYPE,mode="r")
        frame=pd.DataFrame({name:raw_meta[name] for name in META_COLUMNS},copy=False)
        frame.to_parquet(OUT/f"meta_{cg}.parquet",index=False)
        splits[str(cg)]=dict(counts,bills=len(selected),features=len(FEATURES),x_sha256=digest(x_path),meta_sha256=digest(OUT/f"meta_{cg}.parquet"))
        print("DONE PANEL",cg,splits[str(cg)],flush=True)
    (OUT/"feature_names.json").write_text(json.dumps(dict(base=BASE,enhanced=ENHANCED,dynamic=DYNAMIC,public=PUBLIC,all=FEATURES),indent=2))
    (OUT/"identifiers.json").write_text(json.dumps(dict(bills=bill_keys,members=mids,member_names={m:members[m]["name"] for m in mids}),indent=2))
    (OUT/"panel_receipt.json").write_text(json.dumps(dict(splits=splits,sources=RECEIPTS,protocol_sha256=digest(Path(__file__).parent/"PROTOCOL.md"),
                                                       build_script_sha256=digest(__file__),cutoff="2026-09-03",ages=AGES),indent=2))


if __name__=="__main__":
    build()
