"""Audit frozen title pairs against official, version-specific introduced text."""
import collections
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import re
import time
import unicodedata
import xml.etree.ElementTree as ET

import requests

from common import CODE, OLD, OUT, digest, log, read_json, stamp, write_json


def body_tokens(payload):
    root = ET.fromstring(payload)
    if root.tag != "bill" or root.attrib.get("bill-stage") not in {"Introduced-in-House", "Introduced-in-Senate"}:
        raise ValueError("Not introduced bill XML")
    body = root.find("legis-body")
    if body is None:
        raise ValueError("Missing legislative body")
    text = unicodedata.normalize("NFKC", " ".join(body.itertext())).lower()
    return re.findall(r"\w+", text)


def compare(a, b):
    if min(len(a), len(b)) < 40:
        return dict(tokens_current=len(a), tokens_prior=len(b), exact=False, dice=0.0,
                    length_ratio=0.0, close=False, reason="insufficient_body")
    sa = {tuple(a[i:i+5]) for i in range(len(a)-4)}
    sb = {tuple(b[i:i+5]) for i in range(len(b)-4)}
    similarity = 2*len(sa & sb)/(len(sa)+len(sb))
    ratio = min(len(a), len(b))/max(len(a), len(b))
    return dict(tokens_current=len(a), tokens_prior=len(b), exact=a == b, dice=similarity,
                length_ratio=ratio, close=similarity >= .90 and ratio >= .80, reason="compared")


def fetch(b):
    cg, kind, number = b["key"].split(":")
    version = "ih" if kind == "hr" else "is"
    package = f"BILLS-{cg}{kind}{number}{version}"
    session = min(2, int(b["introduced"][:4])-(1789+2*(int(cg)-1))+1)
    url = f"https://www.govinfo.gov/bulkdata/BILLS/{cg}/{session}/{kind}/{package}.xml"
    dest = OUT / "introduced_xml" / f"{package}.xml"
    receipt = dest.with_suffix(".json")
    if receipt.exists():
        r = read_json(receipt)
        if r.get("status") == "ok":
            assert digest(dest) == r["sha256"]
            return b["key"], r
    r = dict(key=b["key"], url=url, version=version, introduction_date=b["introduced"],
             observed_utc=stamp(), path=str(dest), status="error")
    for attempt in range(2):
        try:
            response = requests.get(url, timeout=(10, 30), headers={"User-Agent":"Melange-Cosponsorship-Research/1.0"})
            response.raise_for_status()
            tokens = body_tokens(response.content)
            # The package identity also appears in the bill form metadata.
            root = ET.fromstring(response.content)
            congress_text = " ".join(root.find("form").itertext())
            if str(cg) not in congress_text:
                raise ValueError("Unexpected Congress identity in introduced XML")
            dest.write_bytes(response.content)
            r.update(status="ok", sha256=digest(dest), bytes=len(response.content),
                     body_sha256=hashlib.sha256(" ".join(tokens).encode()).hexdigest(), tokens=len(tokens))
            break
        except (requests.RequestException, ET.ParseError, ValueError, AttributeError) as exc:
            r["error"] = str(exc)[:500]
            if attempt == 0:
                if isinstance(exc, requests.HTTPError) and exc.response.status_code == 404:
                    session = 3-session
                    url = f"https://www.govinfo.gov/bulkdata/BILLS/{cg}/{session}/{kind}/{package}.xml"
                    r['url'] = url
                time.sleep(.5)
    write_json(receipt, r)
    return b["key"], r


def run(repair=False):
    suffix='_v2' if repair else ''
    if (OUT / f"predecessor_audit{suffix}.json").exists():
        raise RuntimeError("Predecessor audit frozen; use the saved audit")
    pairs = {k:v for k,v in read_json(OLD/"analogue_links.json").items() if k.startswith(("117:", "118:"))}
    required = set(pairs) | {p["prior_key"] for p in pairs.values()}
    bills = {}
    for line in (OLD / "bills.jsonl").open(encoding="utf-8"):
        b = json.loads(line)
        if b["key"] in required:
            bills[b["key"]] = b
    assert set(bills) == required
    (OUT / "introduced_xml").mkdir(exist_ok=True)
    log(f"Verifying {len(pairs)} predecessor pairs, {len(required)} introduced XML versions")
    fetched = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(fetch, bills[key]) for key in sorted(required)]
        for i, future in enumerate(as_completed(futures), 1):
            key, r = future.result()
            fetched[key] = r
            if i % 200 == 0:
                log(f"Introduced texts: {i}/{len(required)}; {sum(v['status']!='ok' for v in fetched.values())} errors")
    records = []
    cache = {}
    for key, pair in sorted(pairs.items()):
        pk = pair["prior_key"]
        r = dict(key=key, prior_key=pk, title_method=pair["method"], title_similarity=pair["similarity"],
                 current_title=" | ".join(t["text"] for t in bills[key]["titles"]),
                 prior_title=" | ".join(t["text"] for t in bills[pk]["titles"]),
                 current_url=fetched[key]["url"], prior_url=fetched[pk]["url"], available=False)
        if all(fetched[k]["status"] == "ok" for k in [key, pk]):
            for k in [key, pk]:
                if k not in cache:
                    from pathlib import Path
                    cache[k] = body_tokens(Path(fetched[k]["path"]).read_bytes())
            r.update(available=True, **compare(cache[key], cache[pk]))
        records.append(r)
    counts = {}
    for cg in [117, 118]:
        rows = [r for r in records if r["key"].startswith(str(cg)+":")]
        counts[cg] = dict(pairs=len(rows), available=sum(r["available"] for r in rows),
                          exact=sum(r.get("exact", False) for r in rows), close=sum(r.get("close", False) for r in rows),
                          missing=sum(not r["available"] for r in rows))
    path = OUT / f"predecessor_pairs{suffix}.json"
    write_json(path, records)
    write_json(OUT / f"predecessor_audit{suffix}.json", dict(frozen_utc=stamp(), counts=counts,
        requests=len(fetched), successful=sum(r["status"]=="ok" for r in fetched.values()),
        errors={k:v for k,v in fetched.items() if v["status"]!="ok"},
        pairs_sha256=digest(path), protocol_sha256=digest(CODE/"PROTOCOL.md"), source_pairs_sha256=digest(OLD/"analogue_links.json"),
        rule="Dice >= .90, length ratio >= .80, >=40 body tokens; close text does not establish legal equivalence"))
    log(f"Introduced-text audit complete: {counts}")


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument('--repair-missing',action='store_true')
    run(parser.parse_args().repair_missing)
