"""Freeze the user-requested continuing-member conditional benchmark.

Membership uses IDs only: present in both frozen 117/118 risk panels and the
official September 5, 2026 roster snapshot. No outcome columns are read.
Only writes gold_cohort.json/csv/receipt.json in the current research output.
Run without arguments once; --verify checks an existing frozen artifact set.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/cosponsor_universe_20260905"
OLD = ROOT / "outputs/cosponsor_challengers_20260905"
SNAPSHOT = ROOT / "outputs/cosponsor_refinement_20260905/prospective_20260905"
JSON_PATH = OUT / "gold_cohort.json"
CSV_PATH = OUT / "gold_cohort.csv"
RECEIPT_PATH = OUT / "gold_cohort.receipt.json"
SCHEMA = "cosponsor-continuing-member-gold-cohort-v1"
BIOGUIDE = re.compile(r"[A-Z]\d{6}")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def id_hash(member_ids):
    return hashlib.sha256(("\n".join(sorted(member_ids)) + "\n").encode()).hexdigest()


def official_roster(source_receipt):
    if not source_receipt["captured_utc"].startswith("2026-09-05T"):
        raise ValueError("Expected the frozen September 5, 2026 roster receipt")
    roster, provenance = {}, []
    specs = [
        ("house_members.xml", "House", "./members/member/member-info/bioguideID",
         "https://clerk.house.gov/xml/lists/MemberData.xml"),
        ("senate_members.xml", "Senate", "./member/bioguide_id",
         "https://www.senate.gov/general/contact_information/senators_cfm.xml"),
    ]
    for filename, chamber, selector, official_url in specs:
        path = SNAPSHOT / filename
        expected = source_receipt["sources"][filename]
        blob = path.read_bytes()
        actual = hashlib.sha256(blob).hexdigest()
        if actual != expected["sha256"] or expected["url"] != official_url:
            raise ValueError("Official roster provenance mismatch: " + filename)
        root = ET.fromstring(blob)
        nodes = root.findall(selector)
        selected = 0
        for node in nodes:
            mid = (node.text or "").strip()
            if not mid:  # Vacant House seats have no member Bioguide.
                continue
            if not BIOGUIDE.fullmatch(mid) or mid in roster:
                raise ValueError("Malformed/duplicate roster Bioguide: " + mid)
            roster[mid] = chamber
            selected += 1
        if selected < (400 if chamber == "House" else 90):
            raise ValueError("Unexpectedly incomplete official roster: " + chamber)
        provenance.append(dict(
            path=str(path), chamber=chamber, member_ids=selected,
            url=official_url, sha256=actual,
            observed_started_utc=expected["observed_started_utc"],
            observed_completed_utc=expected["observed_completed_utc"],
            http_last_modified=expected.get("last_modified"),
            xml_publish_date=root.attrib.get("publish-date"),
        ))
    return roster, provenance


def build():
    if any(p.exists() for p in (JSON_PATH, CSV_PATH, RECEIPT_PATH)):
        raise RuntimeError("Gold cohort already exists; use --verify, never silently overwrite")
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    sources = [Path(__file__).resolve(), SNAPSHOT / "source_receipt.json",
               SNAPSHOT / "house_members.xml", SNAPSHOT / "senate_members.xml",
               OLD / "identifiers.json", OLD / "panel_receipt.json",
               OLD / "meta_117.parquet", OLD / "meta_118.parquet"]
    before = {str(p): sha(p) for p in sources}
    source_receipt = read_json(SNAPSHOT / "source_receipt.json")
    roster, roster_provenance = official_roster(source_receipt)
    identifier_ids = read_json(OLD / "identifiers.json")["members"]
    if len(identifier_ids) != len(set(identifier_ids)):
        raise ValueError("Frozen identifier mapping has duplicate IDs")
    member_code = {mid: code for code, mid in enumerate(identifier_ids)}
    panel_receipt = read_json(OLD / "panel_receipt.json")
    chambers, risk_sets, row_codes, row_counts = {}, {}, {}, {}
    for congress in (117, 118):
        path = OLD / f"meta_{congress}.parquet"
        if before[str(path)] != panel_receipt["splits"][str(congress)]["meta_sha256"]:
            raise ValueError("Frozen historical metadata hash mismatch")
        # Explicit projection excludes y, event, duration and every outcome field.
        frame = pd.read_parquet(path, columns=["member", "senate"])
        if not frame.senate.isin([0, 1]).all():
            raise ValueError("Invalid historical chamber flag")
        if not frame.member.between(0, len(identifier_ids) - 1).all():
            raise ValueError("Invalid frozen historical member code")
        by_member = collections.defaultdict(set)
        for code, senate in frame.drop_duplicates().itertuples(index=False, name=None):
            if int(code) != code:
                raise ValueError("Noninteger frozen member code")
            by_member[identifier_ids[int(code)]].add("Senate" if senate else "House")
        chambers[congress] = by_member
        risk_sets[congress] = set(by_member)
        row_codes[congress] = frame.member
        row_counts[congress] = len(frame)
    cohort = sorted(risk_sets[117] & risk_sets[118] & set(roster))
    if not cohort:
        raise ValueError("Empty continuing-member intersection")
    codes = [member_code[mid] for mid in cohort]
    rows = [dict(memberBioguide=mid, member_code=member_code[mid],
                 chamber_117="|".join(sorted(chambers[117][mid])),
                 chamber_118="|".join(sorted(chambers[118][mid])),
                 chamber_2026=roster[mid]) for mid in cohort]
    counts = dict(
        official_roster_members=len(roster),
        official_roster_by_chamber=dict(collections.Counter(roster.values())),
        risk_members_117=len(risk_sets[117]), risk_members_118=len(risk_sets[118]),
        both_historical_risk_members=len(risk_sets[117] & risk_sets[118]),
        cohort_members=len(cohort),
        cohort_by_current_chamber=dict(collections.Counter(roster[mid] for mid in cohort)),
        historical_rows={str(cg): dict(all_rows=row_counts[cg],
                                      cohort_rows=int(row_codes[cg].isin(codes).sum()))
                         for cg in (117, 118)},
    )
    payload = dict(
        schema=SCHEMA, created_utc=started,
        benchmark="Continuing-member conditional benchmark; user shorthand: gold cohort",
        rule="IDs appearing in frozen Congress117 AND Congress118 risk rows AND official September5_2026 roster snapshot",
        member_ids=cohort, member_codes=codes, member_ids_sha256=id_hash(cohort),
        counts=counts, members=rows,
        historical_chamber_definition="Chambers represented in frozen risk rows; House|Senate explicitly records a chamber switch",
        roster_snapshot_date="2026-09-05", roster_captured_utc=source_receipt["captured_utc"],
        official_roster_sources=roster_provenance, pinned_yaml_fallback_used=False,
        interpretation=[
            "Membership is selected using later service status, as explicitly requested. It is not a historical all-member benchmark.",
            "Gold denotes this fixed observed-ID cohort, not validated personality, latent traits, true influence, or causal effects.",
            "Language/media/PUBLIC can be conditional candidates within this cohort; collection and availability limitations still apply.",
            "The rule does not require continuous service or the same chamber across all years; it requires presence in both risk panels and the September5 roster.",
            "No outcomes or feature coverage levels are used to select members. Use identical cohort filtering for every baseline/challenger and both training/testing.",
            "The September5 sources are verified captured snapshots; their individual publication/HTTP modification dates are retained, not silently treated as same-day publications.",
        ],
        excluded_ids={
            "present_both_historical_but_not_current": sorted((risk_sets[117] & risk_sets[118]) - set(roster)),
            "current_and_117_but_not_118": sorted((set(roster) & risk_sets[117]) - risk_sets[118]),
            "current_and_118_but_not_117": sorted((set(roster) & risk_sets[118]) - risk_sets[117]),
        },
    )
    after = {str(p): sha(p) for p in sources}
    if before != after:
        raise RuntimeError("Input changed during cohort extraction")
    OUT.mkdir(exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    receipt = dict(
        schema=SCHEMA + "-receipt", status="PASS_FROZEN_CONDITIONAL_COHORT",
        started_utc=started, completed_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        no_outcomes_read=True, metadata_columns_read=["member", "senate"],
        cohort_size=len(cohort), member_ids_sha256=id_hash(cohort), counts=counts,
        sources=[dict(path=str(p), bytes=p.stat().st_size, sha256_before=before[str(p)],
                      sha256_after=after[str(p)]) for p in sources],
        official_roster_sources=roster_provenance, source_unchanged=True,
        outputs_sha256={p.name: sha(p) for p in (JSON_PATH, CSV_PATH)},
        implementation_sha256=sha(__file__),
    )
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(counts, indent=2))


def load_gold_ids():
    """Verify frozen outputs, then return the sorted membership list for filtering."""
    receipt = read_json(RECEIPT_PATH)
    if receipt.get("status") != "PASS_FROZEN_CONDITIONAL_COHORT":
        raise ValueError("Gold cohort receipt is not frozen")
    for filename, expected in receipt["outputs_sha256"].items():
        if filename not in (JSON_PATH.name, CSV_PATH.name) or sha(OUT / filename) != expected:
            raise ValueError("Gold cohort output hash mismatch: " + filename)
    payload = read_json(JSON_PATH)
    ids = payload["member_ids"]
    if ids != sorted(set(ids)) or len(ids) != receipt["cohort_size"]:
        raise ValueError("Gold cohort member uniqueness/count mismatch")
    if id_hash(ids) != receipt["member_ids_sha256"]:
        raise ValueError("Gold cohort member identity digest mismatch")
    return ids


def verify():
    ids = load_gold_ids()
    receipt = read_json(RECEIPT_PATH)
    for source in receipt["sources"]:
        if sha(source["path"]) != source["sha256_before"]:
            raise ValueError("Frozen cohort source changed: " + source["path"])
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if [row["memberBioguide"] for row in rows] != ids:
        raise ValueError("CSV and JSON membership differ")
    print(json.dumps(dict(status="PASS", cohort_members=len(ids), sources_verified=len(receipt["sources"]))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    verify() if args.verify else build()
