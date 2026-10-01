"""Read-only adapters for the local source snapshots; no existing builders imported."""
from __future__ import annotations
import csv
import hashlib
import json
import math
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

from .core import parse_date

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / "data/staffer_network/reference/congress-legislators/750c0608efb6ef1fc3257ba72c99af3771d35088"
SOURCES = ["data/engine/congestion.json", "data/stance/big5_gold_anchored.json",
           "member_references.json", "votes/HS119_members.csv",
           "data/speech/member_leadership_role_cutoffs_v1.json",
           "outputs/cosponsor_challengers_20260905/bills.jsonl",
           str((REFERENCE / "legislators-current.yaml").relative_to(ROOT)),
           str((REFERENCE / "legislators-historical.yaml").relative_to(ROOT))]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def write_ndjson(path, rows):
    with Path(path).open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+"\n")


def normalize(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9 ]", " ", text)


def term_at(person, day, chamber=None):
    day = parse_date(day)
    matches = [t for t in person.get("terms", []) if parse_date(t["start"]) <= day < parse_date(t["end"])
               and (chamber is None or t["chamber"] == chamber)]
    return max(matches, key=lambda t: t["start"]) if matches else None


def load_members(as_of):
    # Optional dependency is isolated from the production environment.
    sys.path.insert(0, str(ROOT / "tmp/relationship_yaml.zip"))
    import yaml
    people, aliases = {}, defaultdict(set)
    for filename in ("legislators-current.yaml", "legislators-historical.yaml"):
        with (REFERENCE / filename).open(encoding="utf-8") as f:
            rows = yaml.safe_load(f)
        for r in rows:
            bio = r.get("id", {}).get("bioguide")
            if not bio:
                continue
            names = r.get("name", {})
            terms = [dict(start=str(t["start"]), end=str(t["end"]),
                          chamber="House" if t["type"] == "rep" else "Senate",
                          state=t["state"], party=t.get("party", "Unknown"))
                     for t in r.get("terms", []) if t["type"] in {"rep", "sen"}]
            name = names.get("official_full") or names.get("first", "")+" "+names.get("last", "")
            people[bio] = dict(bioguide=bio, name=name, terms=terms)
            for variant in (name, names.get("first", "")+" "+names.get("last", ""),
                            names.get("nickname", "")+" "+names.get("last", "")):
                if len(variant.strip().split()) >= 2:
                    aliases[normalize(variant)].add(bio)
    roster = read_json(ROOT / "data/engine/congestion.json")
    for r in roster:
        aliases[normalize(r["member"])].add(r["bioguide"])
    current, excluded = {}, []
    for r in roster:
        bio = r["bioguide"]
        person = people.get(bio)
        t = term_at(person, as_of) if person else None
        if not t:
            excluded.append(dict(member=r["member"], bioguide=bio, reason="no_dated_service_at_cutoff"))
            continue
        current[bio] = dict(person, name=r["member"], **{k:v for k,v in t.items() if k not in {"start","end"}})
    voteview = {}
    with (ROOT / "votes/HS119_members.csv").open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            bio = r["bioguide_id"]
            if bio in current and r["chamber"] == current[bio]["chamber"]:
                voteview[bio] = {"d1":float(r["nominate_dim1"]) if r["nominate_dim1"] else None,
                                 "d2":float(r["nominate_dim2"]) if r["nominate_dim2"] else None}
    leadership = read_json(ROOT / "data/speech/member_leadership_role_cutoffs_v1.json")["members"]
    for bio, person in current.items():
        person.update(voteview.get(bio, dict(d1=None,d2=None)))
        role = leadership.get(person["name"], {})
        person["leader"] = bool(role and role["current_role_assumed_on"] <= as_of)
        person["leadership_role"] = role.get("current_role")
    aliases = {k:next(iter(v)) for k,v in aliases.items() if len(v)==1}
    return current, aliases, dict(roster_input=len(roster), dated_roster=len(current), excluded=excluded)


def load_traits(members):
    obj = read_json(ROOT / "data/stance/big5_gold_anchored.json")
    traits = {bio:{} for bio in members}
    audit = {}
    for trait, block in obj["traits"].items():
        active = block["status"].startswith("ACTIVE")
        audit[trait] = dict(status=block["status"], used=active and trait in "EAO",
                            source_coverage=block.get("coverage_n"), weights=block.get("selected_weights"))
        for bio, person in members.items():
            traits[bio][trait] = block.get("members", {}).get(person["name"], {}).get(trait) if active else None
    audit["relationship_validation"] = "not established; public estimates; no pair/source-family exclusion"
    return traits, audit


TRIGGER = re.compile(r"\b(friendship|close friends?|best friends?|dear friends?|personal friend|personally|"
                     r"dinner|breakfast|lunch|roommate|vacation|fishing|golf|hang out|hate him|hate her|"
                     r"don.t like|can.t stand|despise|loathe|dislike|betray|liar|love him|love her|"
                     r"good friends?|trusted friend|my wedding|his wedding|her wedding)\b", re.I)
STRONG = re.compile(r"\b(friendship|close friends?|best friends?|roommate|vacation|fishing|"
                    r"dinner|breakfast|lunch|hate him|hate her|can.t stand|despise|loathe|"
                    r"don.t like|love him|love her|wedding)\b", re.I)


def extract_candidates(members, aliases, as_of, start):
    """High-recall text retrieval, deliberately not a personal-sentiment classifier."""
    valid_aliases = {k:v for k,v in aliases.items() if v in members}
    pattern = re.compile(r"\b(?:"+"|".join(re.escape(k) for k in sorted(valid_aliases, key=len, reverse=True))+r")\b")
    by_name = {normalize(p["name"]):bio for bio,p in members.items()}
    counts, dates, candidates = defaultdict(Counter), defaultdict(list), []
    logical_hash = hashlib.sha256()
    con = sqlite3.connect((ROOT / "social_media.db").as_uri()+"?mode=ro", uri=True, timeout=10)
    con.execute("PRAGMA query_only=ON")
    con.execute("BEGIN")
    source_counts = con.execute("SELECT source,count(*),min(date),max(date) FROM speeches GROUP BY source").fetchall()
    scanned, unknown_speaker, triggers = 0, 0, 0
    for rowid, name, day, source, package, text in con.execute(
            "SELECT rowid,member,date,source,package,text FROM speeches WHERE date>=? AND date<=? ORDER BY rowid", (start,as_of)):
        scanned += 1
        logical_hash.update(json.dumps([rowid,name,day,source,package,text],ensure_ascii=False).encode("utf-8"))
        actor = by_name.get(normalize(name)) or valid_aliases.get(normalize(name))
        if actor not in members or not term_at(members[actor],day):
            unknown_speaker += 1
            continue
        counts[actor][source] += 1
        dates[actor].append(day)
        if not text or not TRIGGER.search(text):
            continue
        triggers += 1
        normal = normalize(text)
        # NFKD normalization can change character counts: locate the alias in normalized
        # text, then search original tokens to preserve literal original evidence.
        found = {}
        for m in pattern.finditer(normal):
            target = valid_aliases[m.group()]
            if target == actor or not term_at(members[target],day):
                continue
            literal = re.compile(r"\b"+r"[\W_]+".join(re.escape(w) for w in m.group().split())+r"\b", re.I)
            original = literal.search(text)
            if not original:
                continue
            lo, hi = max(0,original.start()-550), min(len(text),original.end()+650)
            snippet = text[lo:hi]
            matches = list(TRIGGER.finditer(snippet))
            if not matches:
                continue
            priority = 3*len(STRONG.findall(snippet)) + len(matches)
            if target in found and found[target][0] >= priority:
                continue
            found[target] = (priority, snippet, lo, hi)
        for target,(priority,snippet,lo,hi) in found.items():
            eid = hashlib.sha256(f"speech:{rowid}:{actor}:{target}".encode()).hexdigest()[:20]
            candidates.append(dict(evidence_id=eid, actor=actor, target=target, actor_name=members[actor]["name"],
                target_name=members[target]["name"], event_date=day, published_date=day,
                date_basis="corpus_date; publication_date_not_independently_verified", source=source,
                source_locator=f"sqlite:social_media.db#speeches/rowid={rowid}", source_rowid=rowid,
                package=package, source_family=f"{source}:{package}:{day}", episode_id=f"{source}:{package}:{day}",
                text=snippet, excerpt_start=lo, excerpt_end=hi, text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                retrieval_priority=priority, review_status="candidate", attribution="unresolved", naturalness="unknown",
                category="unclassified", sign="unknown"))
    con.rollback()
    con.close()
    candidates.sort(key=lambda r:(-r["retrieval_priority"],r["evidence_id"]))
    coverage = [dict(member=bio,name=p["name"],speech_counts=dict(counts[bio]),
                    first_date=min(dates[bio]) if dates[bio] else None,
                    last_date=max(dates[bio]) if dates[bio] else None) for bio,p in sorted(members.items())]
    return candidates, coverage, dict(scanned=scanned, unknown_or_out_of_service_speaker=unknown_speaker,
        trigger_documents=triggers, candidates=len(candidates), source_counts=source_counts,
        queried_rows_sha256=logical_hash.hexdigest(), query_start=start, query_end=as_of,
        access="SQLite mode=ro; query_only; consistent read transaction")


def context(a,b):
    d1 = abs(a["d1"]-b["d1"]) if a["d1"] is not None and b["d1"] is not None else None
    distance_bin = "missing" if d1 is None else "near" if d1<0.2 else "middle" if d1<0.5 else "far"
    return dict(same_party=a["party"]==b["party"], same_state=a["state"]==b["state"],
                same_chamber=a["chamber"]==b["chamber"], nominate_distance=d1,
                nominate_distance_bin=distance_bin, ego_leader=a["leader"],alter_leader=b["leader"])


def context_key(a,b):
    c=context(a,b)
    return (c["same_party"],c["same_state"],c["nominate_distance_bin"],c["alter_leader"])


def read_bills(members, as_of):
    """All-topic 119th HR/S; complete 30-day eligibility; exact title-family dedup."""
    rows, audit, seen = [], Counter(), set()
    with (ROOT / "outputs/cosponsor_challengers_20260905/bills.jsonl").open(encoding="utf-8") as f:
        for line in f:
            b=json.loads(line)
            if b["congress"] !=119:
                continue
            audit["119_records"]+=1
            sponsor=b["sponsor"]
            day=parse_date(b["introduced"])
            if sponsor not in members or not day or not term_at(members[sponsor],day.isoformat(),b["chamber"]):
                audit["sponsor_outside_dated_target_roster"]+=1
                continue
            if day+timedelta(days=30)>parse_date(as_of):
                audit["incomplete_30_day_window"]+=1
                continue
            titles=b.get("titles") or []
            official=next((t["text"] for t in titles if t.get("kind")=="Official Title as Introduced"),None)
            family=(sponsor,normalize(official)) if official else (sponsor,b["key"])
            if family in seen:
                audit["duplicate_exact_title_family"]+=1
                continue
            seen.add(family)
            joins={}
            withdrawals=0
            for j in b["cosponsors"]:
                joined=parse_date(j.get("date"))
                if joined and day<=joined<=day+timedelta(days=30):
                    # Count first joining, retain withdrawals as an audit; this is not net support.
                    joins[j["member"]]=joined.isoformat()
                    withdrawals+=int(bool(j.get("withdrawn")))
            rows.append(dict(key=b["key"],sponsor=sponsor,date=day.isoformat(),chamber=b["chamber"],
                             area=b.get("policy_area") or "Unknown",joins=joins,
                             title=official,source_updated=b.get("updated"),withdrawals=withdrawals))
    audit["included_bills"]=len(rows)
    audit["policy_areas"]=len({b["area"] for b in rows})
    return sorted(rows,key=lambda b:(b["date"],b["key"])),dict(audit)
