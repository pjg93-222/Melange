"""Read-only source audit and immutable, compact extraction for challenger research."""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/cosponsor_challengers_20260905"
RAW = Path(os.environ["LOCALAPPDATA"]) / "Melange/lda_rebuild/raw"
FINANCE = {"HSBA", "SSBK", "HSAG", "SSAF"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def date(value):
    value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(value[:10] if fmt == "%Y-%m-%d" else value, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def text(node, path, default=""):
    return node.findtext(path, default=default).strip()


def parse_bill(payload):
    root = ET.fromstring(payload)
    b = root if root.tag == "bill" else root.find("bill")
    if b is None:
        raise ValueError("missing bill root")
    introduced = date(text(b, "introducedDate"))
    committees = []
    for c in b.findall("committees/item"):
        for a in c.findall("activities/item"):
            committees.append({"code": text(c, "systemCode").upper().removesuffix("00"),
                               "date": date(text(a, "date")), "activity": text(a, "name")})
    titles = [{"text": text(t, "title"), "kind": text(t, "titleType"),
               "updated": date(text(t, "updateDate"))} for t in b.findall("titles/item")
              if "as introduced" in text(t, "titleType").lower()]
    cosponsors = [{"member": text(c, "bioguideId"), "date": date(text(c, "sponsorshipDate")),
                   "original": text(c, "isOriginalCosponsor").lower() == "true",
                   "withdrawn": date(text(c, "sponsorshipWithdrawnDate"))}
                  for c in b.findall("cosponsors/item")]
    actions = [{"date": date(text(a, "actionDate")), "code": text(a, "actionCode"),
                "type": text(a, "type"), "text": text(a, "text")}
               for a in b.findall("actions/item")]
    congress = int(text(b, "congress"))
    kind = (text(b, "type") or text(b, "billType")).lower()
    number_value = text(b, "number") or text(b, "billNumber")
    if not number_value:
        raise ValueError(f"Missing number; root children: {[(x.tag, (x.text or '')[:60]) for x in b]}")
    number = int(number_value)
    return {"key": f"{congress}:{kind}:{number}", "congress": congress, "type": kind,
            "number": number, "introduced": introduced, "chamber": text(b, "originChamber"),
            "sponsor": text(b, "sponsors/item/bioguideId"), "cosponsors": cosponsors,
            "committees": committees, "titles": titles, "policy_area": text(b, "policyArea/name"),
            "actions": actions, "updated": date(text(b, "updateDate")),
            "finance_at_introduction": any(c["code"] in FINANCE and c["date"] == introduced
                                            and c["activity"].lower() == "referred to" for c in committees)}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    source_receipts, report = [], {"created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "bills": {}, "public_sources": {}}
    dest = OUT / "bills.jsonl"
    if dest.exists():
        raise RuntimeError("Snapshot exists; use it rather than silently replacing frozen inputs")
    with dest.open("w", encoding="utf-8") as out:
        for cg in (116, 117, 118, 119):
            counts, min_date, max_date = collections.Counter(), None, None
            for kind in ("hr", "s"):
                path = RAW / f"billstatus{cg}/BILLSTATUS-{cg}-{kind}.zip"
                before = digest(path)
                source_receipts.append({"path": str(path), "sha256": before, "bytes": path.stat().st_size})
                with zipfile.ZipFile(path) as archive:
                    for name in archive.namelist():
                        if not name.lower().endswith(".xml"):
                            continue
                        b = parse_bill(archive.read(name))
                        assert b["congress"] == cg and b["type"] == kind
                        out.write(json.dumps(b, ensure_ascii=False) + "\n")
                        counts["bills"] += 1
                        counts["cosponsor_records"] += len(b["cosponsors"])
                        counts["missing_join_dates"] += sum(not c["date"] for c in b["cosponsors"])
                        counts["withdrawn_records"] += sum(bool(c["withdrawn"]) for c in b["cosponsors"])
                        counts["introduced_titles"] += bool(b["titles"])
                        counts["finance_at_introduction"] += b["finance_at_introduction"]
                        if b["finance_at_introduction"]:
                            counts["finance_later_join_events"] += sum(c["date"] and c["date"] > b["introduced"] for c in b["cosponsors"])
                            counts["finance_zero_cosponsor_bills"] += not b["cosponsors"]
                        if b["introduced"]:
                            min_date = min(min_date or b["introduced"], b["introduced"])
                            max_date = max(max_date or b["introduced"], b["introduced"])
                if digest(path) != before:
                    raise RuntimeError(f"Input changed during extraction: {path}")
            report["bills"][str(cg)] = dict(counts, first_introduced=min_date, last_introduced=max_date)
            print(f"BILLS {cg}: {report['bills'][str(cg)]}", flush=True)
    public_paths = ["press_stance_final.csv", "data/stance/api_press_stance.csv", "data/stance/hearings_cu.csv",
                    "data/stance/interviews_cu.csv", "data/stance/hearing_stance_final.csv",
                    "data/stance/interview_stance_final.csv", "data/stance/tweet_stance_final.csv"]
    for rel in public_paths:
        path = ROOT / rel
        before = digest(path)
        dates, members, count = collections.Counter(), set(), 0
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                count += 1
                day = date(row.get("date"))
                dates[day[:4] if day else "missing"] += 1
                members.add(row.get("bioguide") or row.get("member") or "")
        source_receipts.append({"path": str(path), "sha256": before, "bytes": path.stat().st_size})
        report["public_sources"][rel] = {"rows": count, "members": len(members), "by_year": dict(sorted(dates.items())), "fields": reader.fieldnames}
    for rel in ["votes/HSall_members.csv", "bill_repository_live.json"]:
        path = ROOT / rel
        source_receipts.append({"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size})
    report["sources"] = source_receipts
    report["extracted_bills_sha256"] = digest(dest)
    (OUT / "data_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["public_sources"], indent=2), flush=True)


if __name__ == "__main__":
    run()
