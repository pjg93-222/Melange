"""Normalize the public Cook table into an isolated descriptive research extract.

Uses only Python's standard library. Does not import any Melange modules.
The source table contains Datawrapper @@ sort suffixes, retained separately.
"""
import csv
import hashlib
import io
import json
import pathlib
import re
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent
RAW = ROOT / "raw" / "dataset.csv"
raw_bytes = RAW.read_bytes()
raw_text = raw_bytes.decode("utf-8-sig")
source = list(csv.DictReader(io.StringIO(raw_text), delimiter="\t"))
assert source and list(source[0]) == ["Dist", "Incumbent", "Incumbent Party", "2026 PVI", "Rank", "2025 PVI"]


def display_and_sort(cell):
    parts = cell.split("@@")
    if len(parts) == 1:
        return cell, ""
    assert len(parts) == 2 and re.fullmatch(r"[0-9]+", parts[1]), repr(cell)
    return parts[0], parts[1]


def pvi_number(label):
    if label == "EVEN":
        return 0
    match = re.fullmatch(r"([DR])\+([1-9][0-9]*)", label)
    assert match, repr(label)
    return int(match[2]) * (-1 if match[1] == "D" else 1)


rows = []
for raw in source:
    district, district_sort = display_and_sort(raw["Dist"])
    pvi, pvi_sort = display_and_sort(raw["2026 PVI"])
    assert re.fullmatch(r"[A-Z]{2}-(?:[0-4][0-9]|5[0-2]|AL)", district), repr(district)
    state, seat = district.split("-")
    rank = int(raw["Rank"])
    assert str(rank) == raw["Rank"]
    rows.append({
        "district_source_cell": raw["Dist"],
        "district_label": district,
        "district_id": state + "-" + ("00" if seat == "AL" else seat),
        "state": state,
        "district_number": 0 if seat == "AL" else int(seat),
        "district_source_sort_key": district_sort,
        "incumbent_source_text": raw["Incumbent"],
        "incumbent_party_source": raw["Incumbent Party"],
        "pvi_2025_label": raw["2025 PVI"],
        "pvi_2025_signed_points": pvi_number(raw["2025 PVI"]),
        "pvi_2026_source_cell": raw["2026 PVI"],
        "pvi_2026_label": pvi,
        "pvi_2026_signed_points": pvi_number(pvi),
        "pvi_2026_source_sort_key": pvi_sort,
        "source_rank_2026": raw["Rank"],
        "boundary_currency_status": "UNVERIFIED-HERE",
    })

assert len(rows) == 435
assert len({row["district_id"] for row in rows}) == 435
assert len({row["state"] for row in rows}) == 50
assert sorted(int(row["source_rank_2026"]) for row in rows) == list(range(1, 436))
rows.sort(key=lambda row: row["district_id"])
csv_path = ROOT / "cook_pvi_2026_districts.csv"
with csv_path.open("w", encoding="utf-8", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

metadata = {
    "source_page_url": "https://www.cookpolitical.com/cook-pvi/2026-partisan-voting-index/district-map-and-list",
    "source_embed_url": "https://datawrapper.dwcdn.net/fejB0/1/",
    "source_asset_url": "https://datawrapper.dwcdn.net/fejB0/1/dataset.csv",
    "source_asset_format": "UTF-8 tab-delimited text; .csv source filename",
    "source_asset_sha256": hashlib.sha256(raw_bytes).hexdigest(),
    "source_embed_sha256": hashlib.sha256((ROOT / "raw" / "datawrapper_fejB0_v1.html").read_bytes()).hexdigest(),
    "article_publication_date": "2026-07-29",
    "embed_last_modified_at": "2026-07-22T15:17:03.000Z",
    "embed_public_version": 1,
    "embed_published_at": None,
    "retrieval_date": "2026-10-05",
    "normalization_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "record_count": len(rows),
    "scope": "Neutral historical district reference; alphabetical display; no production join or model weighting.",
    "signed_points_convention": "D negative, R positive, EVEN zero; parsed rounded labels, not unrounded estimates.",
    "district_id_convention": "State postal code plus two-digit district; 00 means at-large. Original district label and cell retained.",
    "source_rank_note": "Publisher rank preserved verbatim as metadata; no derived priority ranking.",
    "incumbent_note": "Publisher's text at source vintage; not independently verified as current officeholder or candidate.",
    "boundary_currency_status": "UNVERIFIED-HERE; July source vintage predates later reported Missouri map developments.",
    "production_eligibility": "Not assessed; no production model changed.",
}
(ROOT / "cook_pvi_2026_districts.json").write_text(json.dumps({"metadata": metadata, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
checksums = {}
for path in [RAW, ROOT / "raw" / "datawrapper_fejB0_v1.html", csv_path, ROOT / "cook_pvi_2026_districts.json", ROOT / "source_parse_plan.md", pathlib.Path(__file__)]:
    checksums[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
(ROOT / "source_manifest.json").write_text(json.dumps({"metadata": metadata, "sha256": checksums}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"records": len(rows), "states": len({r['state'] for r in rows}), "csv": str(csv_path), "sha256": checksums}, indent=2))
