"""Build A7 machine-local employment-evidence inventory and review ledgers.

This lane is deliberately noncanonical.  It consumes already-held, public-source
artifacts only and never performs network I/O.  It emits:

* a file-level source inventory;
* exact-ID LD-203 lobbyist/registrant affiliation observations;
* FEC employer/occupation observations gated by three independent anchors; and
* a 25,340-row coverage ledger.

Neither an LD-203 registrant association nor a FEC employer field is converted
to an employment interval.  Every emitted row remains REVIEW_REQUIRED and all
promotion counters are zero.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LDA_ROOT = Path(
    r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\normalized"
    r"\lda-source-native\generation-20260830T231200Z"
)
LD203_ROOT = Path(
    r"C:\Users\pgoff\AppData\Local\Melange\lda_rebuild\raw\ld203_sweeps"
)
FEC_WAREHOUSE_ROOT = Path(
    r"C:\Users\pgoff\Mentat\outputs\raw-contributions"
    r"\production-all-20260728T204300"
)
BASELINE_LEDGER = (
    PROJECT_ROOT
    / "audits"
    / "staffer_network"
    / "employment_candidate_coverage_house_senate_20260901_a"
    / "employment_candidate_coverage_25340.ndjson.gz"
)
BASELINE_RECEIPT = BASELINE_LEDGER.with_name("employment_candidate_coverage_receipt.json")

MENTAT_DATABASES = {
    "Community Banks": Path(
        r"C:\Users\pgoff\Mentat\tmp\production-all-20260728T204300\runs"
        r"\20260728T204315-41296\industries\community-banks\data\mentat.db"
    ),
    "Credit Arms": Path(
        r"C:\Users\pgoff\Mentat\tmp\production-all-20260728T204300\runs"
        r"\20260728T204315-41296\industries\credit-arms\data\mentat.db"
    ),
    "Credit Union": Path(
        r"C:\Users\pgoff\Mentat\tmp\production-all-20260728T204300\runs"
        r"\20260728T204315-41296\industries\credit-union\data\mentat.db"
    ),
    "Crypto": Path(
        r"C:\Users\pgoff\Mentat\tmp\production-all-20260728T204300\runs"
        r"\20260728T204315-41296\industries\crypto\data\mentat.db"
    ),
    "Fintech": Path(
        r"C:\Users\pgoff\Mentat\tmp\production-remaining-10lane-20260729T1235"
        r"\runs\20260729T123437-15692\industries\fintech\data\mentat.db"
    ),
    "Property & Casualty Insurance": Path(
        r"C:\Users\pgoff\Mentat\tmp\production-all-20260728T204300\runs"
        r"\20260728T204315-41296\industries\property-casualty-insurance"
        r"\data\mentat.db"
    ),
    "Telecom": Path(
        r"C:\Users\pgoff\Mentat\tmp\production-remaining-10lane-20260729T1235"
        r"\runs\20260729T123437-15692\industries\telecom\data\mentat.db"
    ),
}

OTHER_LOCAL_SOURCES = {
    "current_contact_free_staff_directory": PROJECT_ROOT
    / "data"
    / "members"
    / "staff_directory.json",
    "legacy_contact_free_staff_directory": PROJECT_ROOT
    / "CLEAN_STATE_2026-07-05_1932"
    / "staff_directory.json",
    "quorum_master_restricted": PROJECT_ROOT / "Quorum Master.xlsx",
    "politico_directory_already_a3": Path(
        r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\raw\politico"
        r"\crawl-20260829T221300-0400\directory_rows.ndjson"
    ),
    "littlesis_entities_already_a3": Path(
        r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\raw\littlesis"
        r"\snapshot-20260830T062400Z\entities.json.gz"
    ),
    "littlesis_relationships_already_a3": Path(
        r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\raw\littlesis"
        r"\snapshot-20260830T062400Z\relationships.json.gz"
    ),
}

LD203_YEARS = tuple(range(2021, 2027))
EXPECTED_LDA_PEOPLE = 25_340
EXPECTED_LD203_REPORTS = 210_562
EXPECTED_FEC_CONTRIBUTIONS = 1_615_346


class A7BuildError(RuntimeError):
    """Fail-closed build error."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def read_json_with_hash(path: Path) -> tuple[Any, int, str]:
    raw = path.read_bytes()
    return json.loads(raw), len(raw), sha256_bytes(raw)


def iter_gzip_ndjson(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise A7BuildError(f"{path}:{line_number}: expected JSON object")
            yield value


def write_deterministic_gzip(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("wb") as raw_stream:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            compresslevel=6,
            fileobj=raw_stream,
            mtime=0,
        ) as gzip_stream:
            with io.TextIOWrapper(gzip_stream, encoding="utf-8", newline="\n") as stream:
                for row in rows:
                    stream.write(canonical_json_bytes(row).decode("utf-8"))
                    count += 1
    return count


def write_json(path: Path, value: Any) -> None:
    with path.open("wb") as stream:
        stream.write(canonical_json_bytes(value))


def normalized_tokens(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.upper().replace("&", " AND ")
    return tuple(re.findall(r"[A-Z0-9]+", text))


def normalize_org(value: Any) -> str:
    return " ".join(normalized_tokens(value))


def normalize_person_name(value: Any) -> str:
    """Normalize `LAST, FIRST M` and `FIRST M LAST` to the same exact token key."""

    if value is None:
        return ""
    raw = " ".join(str(value).split())
    if "," in raw:
        last, remainder = raw.split(",", 1)
        return " ".join((*normalized_tokens(remainder), *normalized_tokens(last)))
    return " ".join(normalized_tokens(raw))


def valid_fec_date(value: Any) -> str | None:
    if value is None:
        return None
    literal = str(value).strip()[:10]
    try:
        parsed = date.fromisoformat(literal)
    except ValueError:
        return None
    if parsed.year < 2021 or parsed.year > 2026:
        return None
    return parsed.isoformat()


def file_receipt(path: Path, rows: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if rows is not None:
        result["rows"] = rows
    return result


def load_lda_people_and_orgs() -> tuple[
    list[dict[str, Any]],
    dict[str, list[str]],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    receipt_path = LDA_ROOT / "lda_source_native_corpus_receipt.json"
    receipt = read_json(receipt_path)
    if receipt.get("status") != "PASS" or receipt.get("lobbyists") != EXPECTED_LDA_PEOPLE:
        raise A7BuildError("sealed LDA source-native receipt is not the expected PASS census")
    by_role = {item["role"]: item for item in receipt["files"]}
    person_path = LDA_ROOT / by_role["lobbyist_assertions"]["path"]
    org_path = LDA_ROOT / by_role["organization_assertions"]["path"]
    for role, path in (("lobbyist_assertions", person_path), ("organization_assertions", org_path)):
        expected = by_role[role]
        if path.stat().st_size != expected["bytes"] or sha256_file(path) != expected["sha256"]:
            raise A7BuildError(f"sealed LDA {role} hash/size mismatch")

    people = list(iter_gzip_ndjson(person_path))
    if len(people) != EXPECTED_LDA_PEOPLE:
        raise A7BuildError("LDA person row count mismatch")
    ids = [str(row["source_person_id"]) for row in people]
    if len(set(ids)) != EXPECTED_LDA_PEOPLE:
        raise A7BuildError("LDA person IDs are not unique")

    name_index: dict[str, list[str]] = defaultdict(list)
    for row in people:
        person_id = str(row["source_person_id"])
        variants = set(row.get("name_variants") or [])
        variants.add(str(row.get("display_name") or ""))
        for variant in variants:
            key = normalize_person_name(variant)
            if key and person_id not in name_index[key]:
                name_index[key].append(person_id)

    organizations: dict[str, dict[str, Any]] = {}
    org_count = 0
    for row in iter_gzip_ndjson(org_path):
        org_count += 1
        org_id = str(row["source_org_id"])
        keys = {
            normalize_org(row.get("display_name")),
            *(normalize_org(value) for value in row.get("name_variants") or []),
        }
        keys.discard("")
        organizations[org_id] = {
            "display_name": row.get("display_name"),
            "organization_kind": row.get("organization_kind"),
            "name_keys": sorted(keys),
        }
    if org_count != int(receipt["registrants"]) + int(receipt["clients"]):
        raise A7BuildError("LDA organization row count mismatch")
    return people, name_index, organizations, receipt


def report_period_bounds(year: int, period: str) -> tuple[str | None, str | None]:
    if period == "mid_year":
        return f"{year:04d}-01-01", f"{year:04d}-07-01"
    if period == "year_end":
        return f"{year:04d}-07-01", f"{year + 1:04d}-01-01"
    return None, None


def ld203_name(lobbyist: dict[str, Any]) -> str:
    return " ".join(
        str(lobbyist.get(field) or "").strip()
        for field in ("first_name", "middle_name", "last_name", "suffix")
        if str(lobbyist.get(field) or "").strip()
    )


def build_ld203_lane(
    people_by_id: dict[str, dict[str, Any]],
    organizations: dict[str, dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, dict[str, Any]]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    candidates: list[dict[str, Any]] = []
    person_registrants: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    source_files: list[dict[str, Any]] = []
    seen_filings: dict[str, str] = {}
    counters: Counter[str] = Counter()
    filer_types: Counter[str] = Counter()
    top_level_fields: set[str] = set()
    registrant_fields: set[str] = set()
    lobbyist_fields: set[str] = set()
    pac_fields: set[str] = set()
    contribution_item_fields: set[str] = set()

    for year in LD203_YEARS:
        year_root = LD203_ROOT / str(year)
        receipt_path = year_root / "receipt.json"
        receipt, receipt_bytes, receipt_sha = read_json_with_hash(receipt_path)
        if not receipt.get("complete"):
            raise A7BuildError(f"LD-203 {year} receipt is incomplete")
        pages = int(receipt["pages"])
        expected_count = int(receipt["count"])
        source_files.append(
            {
                "bytes": receipt_bytes,
                "path": str(receipt_path.resolve()),
                "records": 0,
                "role": "ld203_year_receipt",
                "sha256": receipt_sha,
                "year": year,
            }
        )
        year_rows = 0
        for page_number in range(1, pages + 1):
            page_path = year_root / f"page_{page_number:05d}.json"
            page, page_bytes, page_sha = read_json_with_hash(page_path)
            results = page.get("results")
            if not isinstance(results, list) or int(page.get("count", -1)) != expected_count:
                raise A7BuildError(f"malformed LD-203 page {page_path}")
            source_files.append(
                {
                    "bytes": page_bytes,
                    "page": page_number,
                    "path": str(page_path.resolve()),
                    "records": len(results),
                    "role": "ld203_api_page",
                    "sha256": page_sha,
                    "year": year,
                }
            )
            year_rows += len(results)
            for result in results:
                counters["reports_scanned"] += 1
                top_level_fields.update(result)
                registrant = result.get("registrant")
                lobbyist = result.get("lobbyist")
                if isinstance(registrant, dict):
                    registrant_fields.update(registrant)
                if isinstance(lobbyist, dict):
                    lobbyist_fields.update(lobbyist)
                for pac in result.get("pacs") or []:
                    if isinstance(pac, dict):
                        pac_fields.update(pac)
                for item in result.get("contribution_items") or []:
                    if isinstance(item, dict):
                        contribution_item_fields.update(item)
                filing_uuid = str(result.get("filing_uuid") or "").strip()
                if not filing_uuid:
                    raise A7BuildError("LD-203 result is missing filing_uuid")
                filing_digest = sha256_bytes(
                    json.dumps(
                        result,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                )
                prior_digest = seen_filings.get(filing_uuid)
                if prior_digest is not None:
                    if prior_digest != filing_digest:
                        raise A7BuildError(
                            f"conflicting duplicate LD-203 filing UUID: {filing_uuid!r}"
                        )
                    counters["identical_duplicate_source_rows"] += 1
                    continue
                seen_filings[filing_uuid] = filing_digest
                counters["unique_reports"] += 1
                filer_type = str(result.get("filer_type") or "NULL")
                filer_types[filer_type] += 1
                if filer_type != "lobbyist" or not isinstance(lobbyist, dict):
                    counters["excluded_not_lobbyist_filer"] += 1
                    continue
                numeric_id = lobbyist.get("id")
                if numeric_id is None:
                    counters["excluded_missing_lobbyist_id"] += 1
                    continue
                person_id = f"lda:lobbyist:{int(numeric_id)}"
                if person_id not in people_by_id:
                    counters["excluded_outside_25340_census"] += 1
                    continue
                if not isinstance(registrant, dict) or registrant.get("id") is None:
                    counters["excluded_missing_registrant"] += 1
                    continue
                registrant_id = f"lda:registrant:{int(registrant['id'])}"
                source_org = organizations.get(registrant_id)
                if not source_org or source_org.get("organization_kind") != "registrant":
                    counters["excluded_registrant_not_in_source_native"] += 1
                    continue
                raw_person_name = ld203_name(lobbyist)
                source_name_key = normalize_person_name(raw_person_name)
                lda_name_keys = {
                    normalize_person_name(value)
                    for value in (
                        *(people_by_id[person_id].get("name_variants") or []),
                        people_by_id[person_id].get("display_name"),
                    )
                    if value
                }
                raw_registrant_name = str(registrant.get("name") or "").strip()
                registrant_name_key = normalize_org(raw_registrant_name)
                name_keys = set(source_org["name_keys"])
                if registrant_name_key:
                    name_keys.add(registrant_name_key)
                period_start, period_end = report_period_bounds(
                    int(result["filing_year"]), str(result.get("filing_period") or "")
                )
                candidate_key = (
                    f"a7-ld203-affiliation\0{person_id}\0{filing_uuid}\0{registrant_id}"
                )
                candidate = {
                    "candidate_id": "a7:ld203:" + hashlib.sha256(candidate_key.encode()).hexdigest(),
                    "candidate_kind": "LD203_LOBBYIST_REGISTRANT_AFFILIATION_OBSERVATION",
                    "canonical_employment_promoted": False,
                    "canonical_identity_promoted": False,
                    "complete_history_asserted": False,
                    "employment_interval_asserted": False,
                    "employment_semantics": (
                        "Official LD-203 associates the exact LDA lobbyist ID with a "
                        "registrant in a dated contribution report; it does not by itself "
                        "prove employment or tenure bounds."
                    ),
                    "filing_period": result.get("filing_period"),
                    "filing_period_end_exclusive": period_end,
                    "filing_period_start": period_start,
                    "filing_type": result.get("filing_type"),
                    "filing_uuid": filing_uuid,
                    "filing_year": int(result["filing_year"]),
                    "identity_anchor": "EXACT_LDA_NUMERIC_ID",
                    "identity_status": "REVIEW_REQUIRED",
                    "lda_registrant_id": registrant_id,
                    "lda_registrant_name": source_org["display_name"],
                    "lda_source_person_id": person_id,
                    "name_consistent_with_source_native": source_name_key in lda_name_keys,
                    "no_contributions": bool(result.get("no_contributions")),
                    "organization_status": "REVIEW_REQUIRED",
                    "raw_lobbyist_name": raw_person_name,
                    "raw_registrant_name": raw_registrant_name,
                    "retrieval_source": "already_held_machine_local_official_api_page",
                    "review_disposition": "REVIEW_REQUIRED",
                    "schema_id": "staffer-network-a7-ld203-affiliation-candidate-v1",
                    "source_as_of": result.get("dt_posted"),
                    "source_locator": result.get("filing_document_url") or result.get("url"),
                    "source_person_numeric_id": int(numeric_id),
                    "source_system_id": "senate-lda-ld203-api",
                }
                candidates.append(candidate)
                counters["candidates_emitted"] += 1
                if candidate["name_consistent_with_source_native"]:
                    counters["name_consistent"] += 1
                else:
                    counters["name_inconsistent_review_flags"] += 1

                support = person_registrants[person_id].setdefault(
                    registrant_id,
                    {
                        "filing_uuids": [],
                        "first_source_as_of": None,
                        "last_source_as_of": None,
                        "name_keys": set(),
                        "registrant_name": source_org["display_name"],
                    },
                )
                support["filing_uuids"].append(filing_uuid)
                support["name_keys"].update(name_keys)
                source_as_of = str(result.get("dt_posted") or "")
                if source_as_of:
                    first = support["first_source_as_of"]
                    last = support["last_source_as_of"]
                    support["first_source_as_of"] = min(first, source_as_of) if first else source_as_of
                    support["last_source_as_of"] = max(last, source_as_of) if last else source_as_of
        if year_rows != expected_count:
            raise A7BuildError(
                f"LD-203 {year} count mismatch: receipt={expected_count}, pages={year_rows}"
            )
    if counters["reports_scanned"] != EXPECTED_LD203_REPORTS:
        raise A7BuildError("LD-203 all-year count mismatch")

    candidates.sort(key=lambda row: (row["filing_year"], row["filing_uuid"], row["candidate_id"]))
    for registrants in person_registrants.values():
        for support in registrants.values():
            support["filing_uuids"].sort()
            support["name_keys"] = sorted(support["name_keys"])
    stats = {
        **dict(sorted(counters.items())),
        "filer_type_counts": dict(sorted(filer_types.items())),
        "people_with_candidates": len(person_registrants),
        "schema": {
            "contribution_item_fields": sorted(contribution_item_fields),
            "lobbyist_fields": sorted(lobbyist_fields),
            "pac_fields": sorted(pac_fields),
            "registrant_fields": sorted(registrant_fields),
            "top_level_fields": sorted(top_level_fields),
        },
    }
    return candidates, person_registrants, source_files, stats


def load_fec_catalog() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    catalog_path = FEC_WAREHOUSE_ROOT / "catalog.json"
    catalog = read_json(catalog_path)
    if catalog.get("status") != "succeeded" or catalog.get("industry_count") != 7:
        raise A7BuildError("unexpected FEC warehouse catalog")
    source_files = [
        {
            **file_receipt(catalog_path),
            "records": 7,
            "role": "fec_warehouse_catalog",
        }
    ]
    schema: list[dict[str, Any]] | None = None
    manifests: dict[str, Any] = {}
    total_rows = 0
    for industry in catalog["industries"]:
        manifest_path = FEC_WAREHOUSE_ROOT / industry["snapshot_manifest"]
        manifest = read_json(manifest_path)
        if manifest.get("logical_sha256") != industry.get("logical_sha256"):
            raise A7BuildError(f"FEC logical hash mismatch for {industry['industry']}")
        observed_schema = manifest["tables"]["contributions"]["schema"]
        if schema is None:
            schema = observed_schema
        elif observed_schema != schema:
            raise A7BuildError("FEC contribution schema differs across industries")
        expected_rows = int(industry["rows"]["contributions"])
        if int(manifest["tables"]["contributions"]["row_count"]) != expected_rows:
            raise A7BuildError("FEC manifest/catalog contribution count mismatch")
        total_rows += expected_rows
        source_files.append(
            {
                **file_receipt(manifest_path),
                "industry": industry["industry"],
                "records": int(manifest["partition_count"]),
                "role": "fec_warehouse_snapshot_manifest",
            }
        )
        manifests[industry["industry"]] = manifest
    if total_rows != EXPECTED_FEC_CONTRIBUTIONS:
        raise A7BuildError("FEC warehouse total contribution count mismatch")
    assert schema is not None
    return catalog, {"columns": schema}, source_files


def fec_source_rows(
    catalog: dict[str, Any],
    source_files: list[dict[str, Any]],
) -> Iterator[tuple[dict[str, Any], str]]:
    for industry in catalog["industries"]:
        manifest_path = FEC_WAREHOUSE_ROOT / industry["snapshot_manifest"]
        manifest = read_json(manifest_path)
        industry_rows = 0
        for partition in sorted(
            manifest["partitions"],
            key=lambda row: (int(row["cycle"]), str(row["company"])),
        ):
            partition_root = FEC_WAREHOUSE_ROOT / partition["path"]
            file_meta = partition_root / "manifest.json"
            partition_manifest = read_json(file_meta)
            expected = partition_manifest["tables"]["contributions"]["files"]["jsonl_gzip"]
            data_path = partition_root / Path(expected["path"]).name
            observed_size = data_path.stat().st_size
            observed_sha = sha256_file(data_path)
            if observed_size != int(expected["bytes"]) or observed_sha != expected["sha256"]:
                raise A7BuildError(f"FEC partition hash/size mismatch: {data_path}")
            rows = int(partition_manifest["tables"]["contributions"]["row_count"])
            source_files.append(
                {
                    "bytes": observed_size,
                    "company": partition["company"],
                    "cycle": int(partition["cycle"]),
                    "industry": industry["industry"],
                    "path": str(data_path.resolve()),
                    "records": rows,
                    "role": "fec_contributions_jsonl_gzip",
                    "sha256": observed_sha,
                }
            )
            observed_rows = 0
            relative_path = data_path.relative_to(FEC_WAREHOUSE_ROOT).as_posix()
            for row in iter_gzip_ndjson(data_path):
                observed_rows += 1
                yield row, relative_path
            if observed_rows != rows:
                raise A7BuildError(f"FEC partition row count mismatch: {data_path}")
            industry_rows += observed_rows
        if industry_rows != int(industry["rows"]["contributions"]):
            raise A7BuildError(f"FEC industry row count mismatch: {industry['industry']}")


def build_fec_lane(
    catalog: dict[str, Any],
    name_index: dict[str, list[str]],
    person_registrants: dict[str, dict[str, dict[str, Any]]],
    source_files: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    counters: Counter[str] = Counter()
    candidates_by_source: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    duplicate_material: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)

    for row, relative_path in fec_source_rows(catalog, source_files):
        counters["rows_scanned"] += 1
        if bool(row.get("is_entity_contributor")):
            counters["excluded_entity_contributor"] += 1
            continue
        observation_date = valid_fec_date(row.get("contribution_receipt_date"))
        if not observation_date:
            counters["excluded_missing_or_out_of_window_date"] += 1
            continue
        employer_key = normalize_org(row.get("contributor_employer"))
        if not employer_key:
            counters["excluded_missing_employer"] += 1
            continue
        name_key = normalize_person_name(row.get("contributor_name"))
        person_ids = name_index.get(name_key, [])
        if len(person_ids) != 1:
            if len(person_ids) > 1:
                counters["excluded_ambiguous_lda_name_key"] += 1
            else:
                counters["excluded_no_exact_lda_name"] += 1
            continue
        person_id = person_ids[0]
        registrants = person_registrants.get(person_id, {})
        matching_registrants = []
        for registrant_id, support in registrants.items():
            if employer_key in support["name_keys"]:
                matching_registrants.append((registrant_id, support))
        if not matching_registrants:
            counters["excluded_no_exact_ld203_registrant_employer_anchor"] += 1
            continue
        sub_id = str(row.get("sub_id") or "").strip()
        if not sub_id:
            counters["excluded_missing_sub_id"] += 1
            continue
        source_key = (sub_id, person_id, observation_date, employer_key)
        material = {
            field: row.get(field)
            for field in (
                "committee_id",
                "committee_name",
                "contributor_employer",
                "contributor_name",
                "contributor_occupation",
                "contribution_receipt_amount",
                "contribution_receipt_date",
                "entity_type",
                "image_number",
                "pdf_url",
                "sub_id",
                "transaction_id",
            )
        }
        material_digest = sha256_bytes(canonical_json_bytes(material))
        duplicate_material[source_key].add(material_digest)
        existing = candidates_by_source.get(source_key)
        if existing is None:
            anchor_rows = []
            for registrant_id, support in sorted(matching_registrants):
                filings = support["filing_uuids"]
                anchor_rows.append(
                    {
                        "first_source_as_of": support["first_source_as_of"],
                        "last_source_as_of": support["last_source_as_of"],
                        "lda_registrant_id": registrant_id,
                        "lda_registrant_name": support["registrant_name"],
                        "ld203_filing_count": len(filings),
                        "ld203_filing_uuid_digest": sha256_bytes(
                            canonical_json_bytes(sorted(filings))
                        ),
                        "ld203_filing_uuid_sample": sorted(filings)[:5],
                    }
                )
            candidate_key = f"a7-fec-employer\0{person_id}\0{sub_id}\0{observation_date}\0{employer_key}"
            existing = {
                "anchor_policy": (
                    "exact unique normalized LDA name + exact normalized FEC employer "
                    "equals a source-native LDA registrant name + the exact LDA numeric "
                    "person ID filed at least one LD-203 report under that registrant"
                ),
                "candidate_id": "a7:fec:" + hashlib.sha256(candidate_key.encode()).hexdigest(),
                "candidate_kind": "FEC_REPORTED_EMPLOYER_OCCUPATION_POINT_OBSERVATION",
                "canonical_employment_promoted": False,
                "canonical_identity_promoted": False,
                "complete_history_asserted": False,
                "employment_interval_asserted": False,
                "employment_semantics": (
                    "The FEC row reports employer/occupation on a dated transaction. "
                    "It is a point observation, not a tenure start, end, or complete history."
                ),
                "fec_committee_id": row.get("committee_id"),
                "fec_committee_name": row.get("committee_name"),
                "fec_pdf_url": row.get("pdf_url"),
                "fec_source_record_digest": material_digest,
                "fec_sub_id": sub_id,
                "fec_transaction_id": row.get("transaction_id"),
                "identity_anchor_count": 3,
                "identity_status": "REVIEW_REQUIRED",
                "lda_registrant_anchors": anchor_rows,
                "lda_source_person_id": person_id,
                "observation_date": observation_date,
                "observation_precision": "day",
                "organization_status": "REVIEW_REQUIRED",
                "raw_contributor_name": row.get("contributor_name"),
                "raw_employer": row.get("contributor_employer"),
                "raw_occupation": row.get("contributor_occupation"),
                "review_disposition": "REVIEW_REQUIRED",
                "schema_id": "staffer-network-a7-fec-employment-observation-candidate-v1",
                "source_employer_key": employer_key,
                "source_name_key": name_key,
                "source_paths": [relative_path],
                "source_system_id": "fec-raw-contribution-warehouse",
            }
            candidates_by_source[source_key] = existing
            counters["candidate_rows_first_seen"] += 1
        elif relative_path not in existing["source_paths"]:
            existing["source_paths"].append(relative_path)
            counters["duplicate_source_partition_support"] += 1

    conflicting = {key for key, digests in duplicate_material.items() if len(digests) != 1}
    candidates = []
    for key, candidate in candidates_by_source.items():
        if key in conflicting:
            counters["excluded_conflicting_duplicate_material"] += 1
            continue
        candidate["source_paths"].sort()
        candidates.append(candidate)
    candidates.sort(key=lambda row: row["candidate_id"])
    counters["candidates_emitted"] = len(candidates)
    counters["people_with_candidates"] = len(
        {row["lda_source_person_id"] for row in candidates}
    )
    return candidates, dict(sorted(counters.items()))


def baseline_by_person() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    receipt = read_json(BASELINE_RECEIPT)
    expected = receipt["output"]
    if (
        BASELINE_LEDGER.stat().st_size != int(expected["bytes"])
        or sha256_file(BASELINE_LEDGER) != expected["sha256"]
    ):
        raise A7BuildError("baseline A4 coverage ledger does not match its receipt")
    rows: dict[str, dict[str, Any]] = {}
    for row in iter_gzip_ndjson(BASELINE_LEDGER):
        person_id = str(row["lda_source_person_id"])
        if person_id in rows:
            raise A7BuildError("duplicate person in baseline A4 coverage")
        rows[person_id] = row
    if len(rows) != EXPECTED_LDA_PEOPLE:
        raise A7BuildError("baseline A4 coverage does not conserve 25,340 people")
    return rows, receipt


def inventory_mentat_databases() -> list[dict[str, Any]]:
    results = []
    for industry, path in MENTAT_DATABASES.items():
        if not path.is_file():
            raise A7BuildError(f"missing Mentat source database: {path}")
        uri = path.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=60)) as connection:
            quick = [str(row[0]) for row in connection.execute("PRAGMA quick_check")]
            columns = [
                {
                    "default": row[4],
                    "name": str(row[1]),
                    "not_null": bool(row[3]),
                    "ordinal": int(row[0]),
                    "primary_key_ordinal": int(row[5]),
                    "sqlite_type": str(row[2]),
                }
                for row in connection.execute("PRAGMA table_info(contributions)")
            ]
            counts = {
                table: int(
                    connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                )
                for table in ("companies", "contributions", "corporate_giving")
            }
        results.append(
            {
                **file_receipt(path),
                "industry": industry,
                "quick_check": quick,
                "table_counts": counts,
                "contributions_schema": columns,
            }
        )
    return results


def inventory_other_sources() -> list[dict[str, Any]]:
    results = []
    for role, path in OTHER_LOCAL_SOURCES.items():
        if not path.is_file():
            results.append({"path": str(path.resolve()), "role": role, "status": "MISSING"})
            continue
        item: dict[str, Any] = {**file_receipt(path), "role": role, "status": "PRESENT"}
        if role.endswith("staff_directory"):
            directory = read_json(path)
            item["schema"] = "object member_display_name -> array[{id,n,t,star}]"
            item["member_office_keys"] = len(directory)
            item["staff_rows"] = sum(len(value) for value in directory.values())
            item["a7_disposition"] = "NO_DATES_OR_EXACT_LDA_IDS_NAME_ONLY_LINKAGE_PROHIBITED"
        elif role == "quorum_master_restricted":
            item["schema"] = "XLSX_RESTRICTED_CONTACT_SOURCE_NOT_OPENED_IN_A7"
            item["a7_disposition"] = "ALREADY_REMEDIATED_SOURCE_LANE_NO_NEW_EXACT_ID_LINK"
        elif "already_a3" in role:
            item["a7_disposition"] = "ALREADY_COVERED_BY_A3_EXCLUDED_FROM_A7_CANDIDATES"
        results.append(item)
    return results


def output_receipt(path: Path, rows: int) -> dict[str, Any]:
    return {
        "bytes": path.stat().st_size,
        "path": path.name,
        "rows": rows,
        "sha256": sha256_file(path),
    }


def build(output_root: Path, generated_at: str) -> dict[str, Any]:
    if output_root.exists() and any(output_root.iterdir()):
        raise A7BuildError(f"output directory must be empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    people, name_index, organizations, lda_receipt = load_lda_people_and_orgs()
    people_by_id = {str(row["source_person_id"]): row for row in people}
    baseline, baseline_receipt = baseline_by_person()

    ld203_candidates, person_registrants, source_files, ld203_stats = build_ld203_lane(
        people_by_id, organizations
    )
    catalog, fec_schema, fec_inventory = load_fec_catalog()
    source_files.extend(fec_inventory)
    fec_candidates, fec_stats = build_fec_lane(
        catalog, name_index, person_registrants, source_files
    )

    ld203_counts = Counter(row["lda_source_person_id"] for row in ld203_candidates)
    fec_counts = Counter(row["lda_source_person_id"] for row in fec_candidates)
    baseline_no_candidate = {
        person_id
        for person_id, row in baseline.items()
        if not bool(row["coverage_flags"]["has_any_employment_candidate"])
    }
    new_people = set(fec_counts).intersection(baseline_no_candidate)

    coverage_rows = []
    for ordinal, person in enumerate(people, 1):
        person_id = str(person["source_person_id"])
        fec_count = int(fec_counts[person_id])
        ld203_count = int(ld203_counts[person_id])
        prior = baseline[person_id]
        coverage_rows.append(
            {
                "a7_adds_dated_employer_observation_beyond_baseline": bool(
                    fec_count and person_id in baseline_no_candidate
                ),
                "a7_candidate_status": (
                    "REVIEW_REQUIRED" if fec_count or ld203_count else "NO_A7_CANDIDATE"
                ),
                "baseline_has_any_employment_candidate": bool(
                    prior["coverage_flags"]["has_any_employment_candidate"]
                ),
                "canonical_employment_promoted": False,
                "canonical_identity_promoted": False,
                "complete_history_asserted": False,
                "display_name": person.get("display_name"),
                "fec_employer_observation_candidate_count": fec_count,
                "lda_source_person_id": person_id,
                "ld203_affiliation_candidate_count": ld203_count,
                "schema_id": "staffer-network-a7-machine-local-coverage-v1",
                "sealed_queue_ordinal": ordinal,
            }
        )

    inventory = {
        "baseline": {
            "ledger": file_receipt(BASELINE_LEDGER, EXPECTED_LDA_PEOPLE),
            "receipt": file_receipt(BASELINE_RECEIPT),
            "status": baseline_receipt["status"],
        },
        "candidate_policy": {
            "fec": (
                "Emit only when a globally unique exact normalized FEC/LDA name match, "
                "an exact normalized employer/registrant-name match, and an exact numeric "
                "LDA-person-to-registrant LD-203 filing link all agree."
            ),
            "ld203": (
                "Emit exact numeric LDA-person-to-registrant filing associations as dated "
                "affiliation candidates only; never call them employment episodes."
            ),
            "name_only_matches": 0,
            "network_requests": 0,
            "private_credentials_read": 0,
        },
        "fec_contribution_warehouse": {
            "catalog": file_receipt(FEC_WAREHOUSE_ROOT / "catalog.json", 7),
            "columns": fec_schema["columns"],
            "industry_count": 7,
            "partition_count": sum(int(row["partition_count"]) for row in catalog["industries"]),
            "rows": EXPECTED_FEC_CONTRIBUTIONS,
            "root": str(FEC_WAREHOUSE_ROOT.resolve()),
            "snapshots": [
                {
                    "company_count": row["company_count"],
                    "industry": row["industry"],
                    "logical_sha256": row["logical_sha256"],
                    "partition_count": row["partition_count"],
                    "rows": row["rows"]["contributions"],
                    "snapshot_manifest": str(
                        (FEC_WAREHOUSE_ROOT / row["snapshot_manifest"]).resolve()
                    ),
                }
                for row in catalog["industries"]
            ],
        },
        "lda_source_native": {
            "files": lda_receipt["files"],
            "lobbyists": lda_receipt["lobbyists"],
            "organizations": int(lda_receipt["registrants"]) + int(lda_receipt["clients"]),
            "receipt": file_receipt(LDA_ROOT / "lda_source_native_corpus_receipt.json"),
            "root": str(LDA_ROOT.resolve()),
        },
        "ld203": {
            "root": str(LD203_ROOT.resolve()),
            "schema": ld203_stats["schema"],
            "year_receipts": [
                {
                    **read_json(LD203_ROOT / str(year) / "receipt.json"),
                    "path": str((LD203_ROOT / str(year) / "receipt.json").resolve()),
                    "sha256": sha256_file(LD203_ROOT / str(year) / "receipt.json"),
                    "year": year,
                }
                for year in LD203_YEARS
            ],
        },
        "mentat_source_databases": inventory_mentat_databases(),
        "other_local_sources": inventory_other_sources(),
        "schema_id": "staffer-network-a7-machine-local-source-inventory-v1",
    }

    inventory_path = output_root / "a7_source_inventory.json"
    source_files_path = output_root / "a7_source_file_inventory.ndjson.gz"
    ld203_path = output_root / "a7_ld203_affiliation_candidates.ndjson.gz"
    fec_path = output_root / "a7_fec_employment_observation_candidates.ndjson.gz"
    coverage_path = output_root / "a7_coverage_25340.ndjson.gz"

    write_json(inventory_path, inventory)
    source_files.sort(key=lambda row: (row["role"], row["path"]))
    source_file_rows = write_deterministic_gzip(source_files_path, source_files)
    ld203_rows = write_deterministic_gzip(ld203_path, ld203_candidates)
    fec_rows = write_deterministic_gzip(fec_path, fec_candidates)
    coverage_count = write_deterministic_gzip(coverage_path, coverage_rows)

    receipt = {
        "baseline_no_employment_candidate_people": len(baseline_no_candidate),
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "complete_history_assertions": 0,
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
        },
        "expected_scope_size": EXPECTED_LDA_PEOPLE,
        "fec": fec_stats,
        "generated_at": generated_at,
        "ld203": ld203_stats,
        "name_index": {
            "ambiguous_normalized_keys": sum(1 for ids in name_index.values() if len(ids) > 1),
            "normalized_keys": len(name_index),
            "unique_normalized_keys": sum(1 for ids in name_index.values() if len(ids) == 1),
        },
        "new_dated_employer_observation_people_beyond_baseline": len(new_people),
        "outputs": {
            "coverage": output_receipt(coverage_path, coverage_count),
            "fec_candidates": output_receipt(fec_path, fec_rows),
            "inventory": output_receipt(inventory_path, 1),
            "ld203_candidates": output_receipt(ld203_path, ld203_rows),
            "source_file_inventory": output_receipt(source_files_path, source_file_rows),
        },
        "people_with_any_a7_candidate": len(set(ld203_counts) | set(fec_counts)),
        "people_with_fec_employer_observation_candidates": len(fec_counts),
        "people_with_ld203_affiliation_candidates": len(ld203_counts),
        "promotion_policy": "REVIEW_REQUIRED_ZERO_PROMOTIONS",
        "schema_id": "staffer-network-a7-machine-local-source-inventory-receipt-v1",
        "status": "PASS",
    }
    receipt_path = output_root / "a7_build_receipt.json"
    write_json(receipt_path, receipt)
    return {**receipt, "receipt": file_receipt(receipt_path)}


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--generated-at", required=True)
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    options = parse_args(arguments)
    try:
        result = build(options.output_root, options.generated_at)
    except Exception as error:
        print(json.dumps({"status": "FAILED", "error": f"{type(error).__name__}: {error}"}))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
