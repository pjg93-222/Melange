#!/usr/bin/env python3
"""Build a deterministic, source-neutral employment adjudication overlay.

The acquired public-page spans are discovery evidence, not employment facts.
This stage therefore disposes every discovered line, creates conservative
provisional episodes only from structured/corroborated evidence, and keeps all
canonical and lifetime-completeness gates closed until calibrated review passes.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Iterator, Mapping
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "fec") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "fec"))
from staffer_network.schema_validation import validate_instance, validate_schema_definition


METHOD_VERSION = "bulk-employment-adjudication-overlay-v3"
DECISION_SCHEMA = "staffer-network-employment-candidate-adjudication-v2"
EPISODE_SCHEMA = "staffer-network-provisional-employment-episode-v2"
PERSON_SCHEMA = "staffer-network-employment-adjudication-person-summary-v1"
GOLD_SCHEMA = "staffer-network-employment-adjudication-gold-sample-v2"
RECEIPT_SCHEMA = "staffer-network-employment-adjudication-receipt-v2"
SCHEMA_DIRECTORY = PROJECT_ROOT / "fec" / "staffer_network" / "schemas"
SCHEMA_FILES = {
    DECISION_SCHEMA: "employment_candidate_adjudication_v2.schema.json",
    EPISODE_SCHEMA: "provisional_employment_episode_v2.schema.json",
    PERSON_SCHEMA: "employment_adjudication_person_summary.schema.json",
    GOLD_SCHEMA: "employment_adjudication_gold_sample_v2.schema.json",
    RECEIPT_SCHEMA: "employment_adjudication_receipt_v2.schema.json",
}
ALLOWED_DECISIONS = {
    "PROVISIONALLY_ACCEPTED",
    "ACCEPTED_SOURCE_BINDING",
    "ACCEPTED_SOURCE_NATIVE_ASSOCIATION",
    "REJECTED",
    "REVIEW_REQUIRED",
}

WORD = re.compile(r"[a-z0-9]+")
STOP = {
    "a", "an", "and", "at", "for", "from", "in", "of", "on", "the", "to",
    "u", "s", "us", "office", "staff", "sen", "senator", "rep",
    "representative", "committee",
}
NOISE = (
    re.compile(r"^recipient / honoree legislator payee / committee date amount$", re.I),
    re.compile(r"^bills search by number, title, sponsor, chamber, or status\b", re.I),
    re.compile(r"^university programs$", re.I),
    re.compile(r"^executive education$", re.I),
    re.compile(r"^education$", re.I),
    re.compile(r"\b(?:salary|education) records? for people in our database\b", re.I),
    re.compile(r"\b(?:pro subscribers|pro account|pro benefits|subscribe, or log in)\b", re.I),
    re.compile(r"^\.\.\.?$"),
)
OFFICIAL_HOSTS = {
    "www.house.gov", "house.gov", "www.senate.gov", "senate.gov",
    "www.govinfo.gov", "govinfo.gov", "www.congress.gov", "congress.gov",
}
LEGILIST_PROFILE = re.compile(
    r"^https?://(?:www\.)?legilist\.com/lda/contributions/lobbyist/(?P<id>[0-9]+)/",
    re.I,
)
ORG_RANK = {
    "MEMBER_OFFICE_CANDIDATE": 4,
    "COMMITTEE_CANDIDATE": 4,
    "LEADERSHIP_CANDIDATE": 4,
    "GOVERNMENT_BODY_CANDIDATE": 3,
    "ORGANIZATION_CANDIDATE": 2,
    "OTHER_ORG_CANDIDATE": 1,
}


class AdjudicationError(RuntimeError):
    pass


def compact(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(compact(value)).hexdigest()


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise AdjudicationError(f"object required at {path}:{line_number}")
            yield value


def write_gzip(path: Path, values: Iterable[Mapping[str, Any]]) -> tuple[int, str]:
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for value in values:
                stream.write(compact(value))
                count += 1
    return count, sha256(path)


def tokens(value: Any) -> set[str]:
    return {
        token for token in WORD.findall(str(value or "").lower())
        if len(token) > 1 and token not in STOP
    }


def similarity(left: Any, right: Any) -> float:
    a, b = tokens(left), tokens(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def source_urls(value: Mapping[str, Any]) -> list[str]:
    urls = value.get("source_urls")
    if isinstance(urls, list):
        return sorted({str(url) for url in urls if isinstance(url, str) and url})
    url = value.get("source_url")
    return [str(url)] if isinstance(url, str) and url else []


def make_decision(
    *,
    lane: str,
    candidate_id: str,
    person_id: str,
    display_name: str | None,
    decision: str,
    rationale_codes: list[str],
    evidence: Mapping[str, Any],
    proposed_episode_id: str | None = None,
) -> dict[str, Any]:
    if decision not in ALLOWED_DECISIONS:
        raise AdjudicationError(f"invalid decision: {decision}")
    evidence_digest = digest(evidence)
    core = {
        "lane": lane,
        "candidate_id": candidate_id,
        "lda_source_person_id": person_id,
        "display_name": display_name,
        "decision": decision,
        "reviewer_kind": "RULE",
        "reviewer_id": f"rule:{METHOD_VERSION}",
        "rationale_codes": sorted(set(rationale_codes)),
        "evidence_digest": evidence_digest,
        "source_urls": source_urls(evidence),
        "proposed_episode_id": proposed_episode_id,
        "method_version": METHOD_VERSION,
    }
    payload_sha256 = digest(core)
    return {
        "schema_id": DECISION_SCHEMA,
        "decision_id": "adjudication:decision:" + payload_sha256,
        **core,
        "decision_payload_sha256": payload_sha256,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "complete_lifetime_employment_asserted": False,
    }


def ordered_name_in_title(display_name: str | None, title: Any) -> bool:
    parts = [part for part in WORD.findall(str(display_name or "").lower()) if len(part) > 1]
    title_parts = WORD.findall(str(title or "").lower())
    if not parts or not title_parts:
        return False
    anchors = [parts[0]] if len(parts) == 1 else [parts[0], parts[-1]]
    cursor = 0
    for anchor in anchors:
        try:
            cursor = title_parts.index(anchor, cursor) + 1
        except ValueError:
            return False
    return True


def exact_legilist_source_binding(
    candidate: Mapping[str, Any], person_id: str, display_name: str | None
) -> bool:
    match = LEGILIST_PROFILE.match(str(candidate.get("source_url") or ""))
    return bool(
        match
        and match.group("id") == person_id.rsplit(":", 1)[-1]
        and ordered_name_in_title(display_name, candidate.get("source_title"))
    )


def raw_line_disposition(
    candidate: Mapping[str, Any], person_id: str, display_name: str | None
) -> tuple[str, list[str]]:
    line = " ".join(str(candidate.get("line") or "").split())
    url = str(candidate.get("source_url") or "")
    host = (urlsplit(url).hostname or "").lower()
    if any(pattern.search(line) for pattern in NOISE):
        return "REJECTED", ["KNOWN_NAVIGATION_GATE_OR_PLACEHOLDER_LINE"]
    if len(line) < 8:
        return "REJECTED", ["INSUFFICIENT_RELATIONAL_CONTENT"]
    if host in {"legilist.com", "www.legilist.com"} and "/lda/contributions/" in url:
        if exact_legilist_source_binding(candidate, person_id, display_name):
            return "REVIEW_REQUIRED", [
                "EXACT_LEGILIST_SOURCE_PAGE_BINDING",
                "DISCLOSED_POSITION_LINE_REQUIRES_CLAUSE_LEVEL_PARSE",
                "PAGE_YEARS_MUST_NOT_BE_USED_AS_EMPLOYMENT_DATES",
            ]
        return "REVIEW_REQUIRED", [
            "LEGILIST_PAGE_NOT_EXACTLY_BOUND_TO_THIS_LDA_SOURCE_ID",
            "CROSS_ID_OR_FIRM_PAGE_LINE_QUARANTINED",
        ]
    return "REVIEW_REQUIRED", ["UNSTRUCTURED_PAGE_LINE_REQUIRES_RELATION_PARSING"]


def year_bounds(start_year: int, end_year: int) -> dict[str, Any]:
    if start_year < 1800 or end_year > 2100 or start_year > end_year:
        raise AdjudicationError("invalid year range")
    return {
        "valid_start_earliest": f"{start_year:04d}-01-01",
        "valid_start_latest": f"{start_year:04d}-12-31",
        # A stated end year is treated as inclusive but the exact day is unknown.
        "valid_end_earliest": f"{end_year:04d}-01-02",
        "valid_end_latest": f"{end_year + 1:04d}-01-01",
        "start_precision": "year",
        "end_precision": "year",
        "asserted_current": False,
    }


def date_atom_bounds(raw: str, boundary: str, as_of: date) -> tuple[str, str, str, bool]:
    value = raw.strip()
    if value.lower() in {"present", "current", "currently"}:
        if boundary != "end":
            raise AdjudicationError("current marker cannot be a start")
        censored = as_of + timedelta(days=1)
        return censored.isoformat(), censored.isoformat(), "day", True
    if re.fullmatch(r"(?:18|19|20)\d{2}", value):
        year = int(value)
        if boundary == "start":
            return f"{year}-01-01", f"{year}-12-31", "year", False
        return f"{year}-01-02", f"{year + 1}-01-01", "year", False
    match = re.fullmatch(r"((?:18|19|20)\d{2})-(\d{1,2})", value)
    if match:
        year, month = map(int, match.groups())
        first = date(year, month, 1)
        following = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        if boundary == "start":
            return first.isoformat(), (following - timedelta(days=1)).isoformat(), "month", False
        return (first + timedelta(days=1)).isoformat(), following.isoformat(), "month", False
    if re.fullmatch(r"(?:18|19|20)\d{2}-\d{1,2}-\d{1,2}", value):
        parsed = date.fromisoformat(value)
        if boundary == "start":
            return parsed.isoformat(), parsed.isoformat(), "day", False
        exclusive = parsed + timedelta(days=1)
        return exclusive.isoformat(), exclusive.isoformat(), "day", False
    raise AdjudicationError(f"unsupported date atom: {raw}")


def bounds_within_cutoff(bounds: Mapping[str, Any], as_of: date) -> bool:
    """Require a coherent uncertainty quartet bounded by the source cutoff."""

    try:
        start_earliest = date.fromisoformat(str(bounds["valid_start_earliest"]))
        start_latest = date.fromisoformat(str(bounds["valid_start_latest"]))
        end_earliest = date.fromisoformat(str(bounds["valid_end_earliest"]))
        end_latest = date.fromisoformat(str(bounds["valid_end_latest"]))
    except (KeyError, TypeError, ValueError):
        return False
    cutoff = as_of + timedelta(days=1)
    return (
        start_earliest <= start_latest
        and end_earliest <= end_latest
        and start_earliest < end_latest
        and end_latest <= cutoff
    )


def clean_role_and_employer(title: Any, employer: Any) -> bool:
    """Reject obvious extraction truncation and narrative contamination."""

    role = " ".join(str(title or "").split()).strip()
    organization = " ".join(str(employer or "").split()).strip()
    if not role or not organization:
        return False
    if re.search(r"\b(?:and|or|of|the)\s*$", role, re.I):
        return False
    if re.search(r"\.\s*(?:he|she|they|his|her|their)\b", organization, re.I):
        return False
    return True


def normalize_employer_candidate(value: str) -> str:
    return re.sub(r"^(?:18|19|20)\d{2}\s+", "", " ".join(value.split())).strip()


def normalize_title_candidate(value: str) -> str:
    return re.sub(
        r"\s+\(?OTHER COMPENSATION\)?\s*$",
        "",
        " ".join(value.split()),
        flags=re.I,
    ).strip()


def make_episode(
    *,
    lane: str,
    candidate_id: str,
    person_id: str,
    display_name: str | None,
    employer: str,
    title: str,
    bounds: Mapping[str, Any],
    urls: list[str],
    source_as_of: str,
    identity_status: str,
    blockers: list[str],
    temporal_semantics: str,
    observation_intervals: list[dict[str, Any]] | None = None,
    support_candidate_ids: list[str] | None = None,
) -> dict[str, Any]:
    support_ids = sorted(set(support_candidate_ids or [candidate_id]))
    raw_employer = " ".join(employer.split())
    raw_title = " ".join(title.split())
    employer_candidate = normalize_employer_candidate(raw_employer)
    title_candidate = normalize_title_candidate(raw_title)
    core = {
        "lane": lane,
        "person": person_id,
        "employer": employer_candidate.casefold(),
        "title": title_candidate.casefold(),
        "bounds": dict(bounds),
        "temporal_semantics": temporal_semantics,
        "identity_status": identity_status,
        "container_status": "LITERAL_REVIEW_REQUIRED",
    }
    episode_id = "provisional:employment-episode:" + digest(core)
    return {
        "schema_id": EPISODE_SCHEMA,
        "episode_id": episode_id,
        "evidence_lanes": [lane],
        "decision_ids": [],
        "lda_source_person_id": person_id,
        "display_name": display_name,
        "raw_employer": raw_employer,
        "raw_title": raw_title,
        "raw_employer_variants": [raw_employer],
        "raw_title_variants": [raw_title],
        "employer_candidate": employer_candidate,
        "title_candidate": title_candidate,
        **dict(bounds),
        "source_as_of": source_as_of,
        "source_urls": sorted(set(urls)),
        "source_candidate_ids": [candidate_id],
        "support_candidate_ids": support_ids,
        "support_digest": digest(support_ids),
        "identity_status": identity_status,
        "container_status": "LITERAL_REVIEW_REQUIRED",
        "episode_status": "PROVISIONAL",
        "temporal_semantics": temporal_semantics,
        "observation_intervals": observation_intervals or [],
        "promotion_blockers": sorted(set(blockers)),
        "temporal_weight_eligible": False,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "complete_lifetime_employment_asserted": False,
    }


def consolidate_episodes(values: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Collapse exact provisional facts while retaining every evidence decision.

    The episode identifier is independent of the supporting lane and candidate ID,
    so repeated LDA claims or payroll rows cannot become duplicate graph evidence.
    """

    merged: dict[str, dict[str, Any]] = {}
    union_fields = {
        "evidence_lanes", "decision_ids", "source_urls", "source_candidate_ids",
        "support_candidate_ids", "raw_employer_variants", "raw_title_variants",
        "support_digest", "promotion_blockers",
    }
    representative_fields = {
        "raw_employer", "raw_title", "employer_candidate", "title_candidate",
    }
    for value in values:
        row = dict(value)
        episode_id = str(row["episode_id"])
        current = merged.get(episode_id)
        if current is None:
            merged[episode_id] = row
            continue
        if any(
            current.get(key) != row.get(key)
            for key in set(row) - union_fields - representative_fields
        ):
            raise AdjudicationError(f"episode ID collision with different fact: {episode_id}")
        for field in union_fields - {"support_digest"}:
            current[field] = sorted(set(current.get(field) or []) | set(row.get(field) or []))
        current["support_digest"] = digest(current["support_candidate_ids"])
        current["raw_employer"] = min(
            current["raw_employer_variants"], key=lambda value: (value.casefold(), value)
        )
        current["raw_title"] = min(
            current["raw_title_variants"], key=lambda value: (value.casefold(), value)
        )
        current["employer_candidate"] = normalize_employer_candidate(
            current["raw_employer"]
        )
        current["title_candidate"] = normalize_title_candidate(current["raw_title"])
    return sorted(merged.values(), key=lambda row: row["episode_id"])


def clean_covered_candidate(row: Mapping[str, Any]) -> tuple[dict[str, Any], str, str] | None:
    dates = [
        item for item in row.get("date_range_mentions") or []
        if item.get("explicit_start_year") and item.get("explicit_end_year")
        and item.get("open_ended_text") is False and not item.get("review_flags")
    ]
    roles = {
        str(item["text"]).strip() for item in row.get("role_title_mentions") or []
        if item.get("confidence") == "HIGH" and not item.get("generic_title_risk")
        and not item.get("ambiguous_abbreviation") and item.get("text")
    }
    organizations = [
        item for item in row.get("office_employer_mentions") or []
        if item.get("confidence") == "HIGH" and item.get("text")
    ]
    if len(dates) != 1 or len(roles) != 1 or not organizations:
        return None
    best_rank = max(ORG_RANK.get(str(item.get("entity_class")), 0) for item in organizations)
    best = {
        str(item["text"]).strip() for item in organizations
        if ORG_RANK.get(str(item.get("entity_class")), 0) == best_rank
    }
    if len(best) != 1:
        return None
    item = dates[0]
    bounds = year_bounds(int(item["explicit_start_year"]), int(item["explicit_end_year"]))
    return bounds, next(iter(roles)), next(iter(best))


def covered_support_index(covered_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in covered_rows:
        if row.get("explicit_no_position"):
            continue
        roles = [
            str(item.get("text") or "") for item in row.get("role_title_mentions") or []
            if item.get("confidence") == "HIGH" and not item.get("generic_title_risk")
        ]
        organizations = [
            str(item.get("text") or "") for item in row.get("office_employer_mentions") or []
            if item.get("confidence") == "HIGH"
        ]
        if roles and organizations:
            result[str(row["lda_source_person_id"])].append(
                {"claim_id": row["claim_id"], "roles": roles, "organizations": organizations}
            )
    return result


def corroborating_claim(
    row: Mapping[str, Any], index: Mapping[str, list[dict[str, Any]]],
    *, title_key: str, organization_key: str,
) -> tuple[str, float, float] | None:
    best: tuple[str, float, float] | None = None
    for claim in index.get(str(row["lda_source_person_id"]), []):
        title_score = max(
            (similarity(row.get(title_key), value) for value in claim["roles"]), default=0.0
        )
        organization_score = max(
            (similarity(row.get(organization_key), value) for value in claim["organizations"]),
            default=0.0,
        )
        candidate = (str(claim["claim_id"]), title_score, organization_score)
        if best is None or (title_score + organization_score, candidate[0]) > (
            best[1] + best[2], best[0]
        ):
            best = candidate
    if best is not None and best[1] >= 0.34 and best[2] >= 0.20:
        return best
    return None


def structured_person_gate(row: Mapping[str, Any], captures: Mapping[str, Mapping[str, Any]]) -> bool:
    support = row.get("identity_support") or []
    domains = {
        (urlsplit(str(item.get("source_url") or "")).hostname or "").lower()
        for item in support if item.get("source_url")
    }
    captured = sum(
        captures.get(str(item.get("source_url") or ""), {}).get("status") == "CAPTURED"
        for item in support
    )
    return (
        row.get("identity_status") == "VERIFIED_CANDIDATE"
        and row.get("match_confidence") == "VERY_HIGH"
        and len(domains) >= 2
        and captured >= 1
    )


def structured_episode_gate(
    row: Mapping[str, Any], captures: Mapping[str, Mapping[str, Any]], as_of: date
) -> tuple[dict[str, Any], list[str]] | None:
    employer = str(row.get("employer") or "").strip()
    title = str(row.get("title") or "").strip()
    raw_start = str(row.get("raw_start_date") or "").strip()
    raw_end = str(row.get("raw_end_date") or "").strip()
    urls = source_urls(row)
    if (
        not employer or not title or not raw_start or not raw_end or not urls
        or not clean_role_and_employer(title, employer)
    ):
        return None
    if "not exposed" in employer.lower() or "not exposed" in title.lower():
        return None
    domains = {(urlsplit(url).hostname or "").lower() for url in urls}
    if not (len(domains) >= 2 or domains & OFFICIAL_HOSTS):
        return None
    if not any(captures.get(url, {}).get("status") == "CAPTURED" for url in urls):
        return None
    try:
        start_first, start_last, start_precision, _ = date_atom_bounds(raw_start, "start", as_of)
        end_first, end_last, end_precision, asserted_current = date_atom_bounds(raw_end, "end", as_of)
    except (AdjudicationError, ValueError):
        return None
    bounds = {
        "valid_start_earliest": start_first,
        "valid_start_latest": start_last,
        "valid_end_earliest": end_first,
        "valid_end_latest": end_last,
        "start_precision": start_precision,
        "end_precision": end_precision,
        "asserted_current": asserted_current,
    }
    if not bounds_within_cutoff(bounds, as_of):
        return None
    return bounds, urls


def file_entry(
    path: Path, role: str, records: int, schema_id: str, schema_path: Path
) -> dict[str, Any]:
    return {
        "role": role,
        "path": path.name,
        "records": records,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "schema_id": schema_id,
        "schema_sha256": sha256(schema_path),
        "privacy_class": "restricted-local",
        "encoding": "canonical-ndjson-gzip-mtime-0" if path.suffix == ".gz" else "canonical-json-lf",
    }


def deterministic_sample(
    decisions: list[dict[str, Any]], sizes: Mapping[str, int], *, sample_kind: str
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for status, size in sizes.items():
        candidates = sorted(
            (row for row in decisions if row["decision"] == status),
            key=lambda row: hashlib.sha256(row["candidate_id"].encode("utf-8")).hexdigest(),
        )
        for row in candidates[:size]:
            stratum_id = f"{row['lane']}:{status}"
            unit = {
                "schema_id": GOLD_SCHEMA,
                "sample_kind": sample_kind,
                "partition": "CALIBRATION",
                "stratum_id": stratum_id,
                "selection_seed_sha256": digest({
                    "method": METHOD_VERSION,
                    "sample_kind": sample_kind,
                    "stratum_id": stratum_id,
                }),
                "candidate_id": row["candidate_id"],
                "decision_id": row["decision_id"],
                "lane": row["lane"],
                "lda_source_person_id": row["lda_source_person_id"],
                "display_name": row["display_name"],
                "proposed_decision": row["decision"],
                "rationale_codes": row["rationale_codes"],
                "source_urls": row["source_urls"],
                "evidence_digest": row["evidence_digest"],
                "decision_payload_sha256": row["decision_payload_sha256"],
            }
            output.append(unit)
    return sorted(output, key=lambda row: row["candidate_id"])


def deterministic_stratified_sample(
    decisions: list[dict[str, Any]], sizes: Mapping[tuple[str, str], int], *,
    sample_kind: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for (lane, status), size in sizes.items():
        stratum = [
            row for row in decisions
            if row["lane"] == lane and row["decision"] == status
        ]
        if len(stratum) < size:
            raise AdjudicationError(
                f"gold stratum too small: {lane}:{status} {len(stratum)} < {size}"
            )
        output.extend(deterministic_sample(
            stratum, {status: size}, sample_kind=sample_kind
        ))
    return sorted(output, key=lambda row: row["candidate_id"])


def adjudicate(
    *,
    sealed_queue: Path,
    bulk_receipt: Path,
    covered_positions: Path,
    registrant_associations: Path,
    structured_profiles: Path,
    capture_ledger: Path,
    house_payroll: Path,
    senate_payroll: Path,
    output_root: Path,
    as_of: str,
) -> dict[str, Any]:
    sources = (
        sealed_queue, bulk_receipt, covered_positions, registrant_associations,
        structured_profiles, capture_ledger, house_payroll, senate_payroll,
    )
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise AdjudicationError(f"missing inputs: {missing}")
    if output_root.exists() and any(output_root.iterdir()):
        raise AdjudicationError(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    as_of_date = date.fromisoformat(as_of)

    queue_rows = list(rows(sealed_queue))
    people = {
        str(row["lda_source_person_id"]): {
            "display_name": row.get("display_name"),
            "sealed_queue_ordinal": row.get("sealed_queue_ordinal"),
        }
        for row in queue_rows
    }
    if len(queue_rows) != 25340 or len(people) != 25340:
        raise AdjudicationError("sealed queue must contain exactly 25,340 unique identities")

    captures = {str(row["url"]): row for row in rows(capture_ledger)}
    covered_rows = list(rows(covered_positions))
    support_index = covered_support_index(covered_rows)
    covered_by_claim = {str(row["claim_id"]): row for row in covered_rows}
    decisions: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    review_material: dict[str, dict[str, Any]] = {}

    bulk = json.loads(bulk_receipt.read_text(encoding="utf-8"))
    bulk_dir = bulk_receipt.parent
    bulk_seen = 0
    bulk_shard_inputs: dict[str, Path] = {}
    source_pages: dict[tuple[str, str], dict[str, Any]] = {}
    for shard in bulk.get("shards") or []:
        shard_path = bulk_dir / str(shard["path"])
        if (
            not shard_path.is_file()
            or shard_path.stat().st_size != shard.get("bytes")
            or sha256(shard_path) != shard.get("sha256")
        ):
            raise AdjudicationError(f"bulk shard receipt binding failed: {shard_path}")
        bulk_shard_inputs[f"bulk_shard:{shard['path']}"] = shard_path
        shard_seen = 0
        for person in rows(shard_path):
            shard_seen += 1
            person_id = str(person["lda_source_person_id"])
            for kind in ("employment", "education"):
                for candidate in person.get(f"{kind}_candidates") or []:
                    bulk_seen += 1
                    candidate_id = "bulk-line:" + digest({
                        "person": person_id,
                        "kind": kind,
                        "url": candidate.get("source_url"),
                        "line_sha256": candidate.get("line_sha256"),
                    })
                    disposition, reasons = raw_line_disposition(
                        candidate, person_id, person.get("display_name")
                    )
                    decision = make_decision(
                        lane=f"bulk_{kind}_line",
                        candidate_id=candidate_id,
                        person_id=person_id,
                        display_name=person.get("display_name"),
                        decision=disposition,
                        rationale_codes=reasons,
                        evidence=candidate,
                    )
                    decisions.append(decision)
                    review_material[candidate_id] = dict(candidate)
                    url = str(candidate.get("source_url") or "")
                    if LEGILIST_PROFILE.match(url):
                        source_pages.setdefault((person_id, url), {
                            "source_url": url,
                            "source_title": candidate.get("source_title"),
                            "lda_source_person_id": person_id,
                            "display_name": person.get("display_name"),
                        })
        if shard_seen != shard.get("rows"):
            raise AdjudicationError(
                f"bulk shard row conservation failed: {shard_path} {shard_seen} != {shard.get('rows')}"
            )
    expected_bulk = int(bulk.get("employment_candidate_count", 0)) + int(
        bulk.get("education_candidate_count", 0)
    )
    if bulk_seen != expected_bulk:
        raise AdjudicationError(f"bulk candidate conservation failed: {bulk_seen} != {expected_bulk}")
    for (person_id, url), evidence in sorted(source_pages.items()):
        candidate_id = "legilist-source-binding:" + digest({"person": person_id, "url": url})
        if exact_legilist_source_binding(evidence, person_id, evidence.get("display_name")):
            disposition = "ACCEPTED_SOURCE_BINDING"
            reasons = [
                "URL_NUMERIC_ID_EQUALS_LDA_SOURCE_PERSON_ID",
                "ORDERED_FIRST_AND_LAST_NAME_PRESENT_IN_PAGE_TITLE",
                "SOURCE_BINDING_ONLY_NOT_CROSS_SOURCE_MERGE",
            ]
        else:
            disposition = "REVIEW_REQUIRED"
            reasons = ["LEGILIST_SOURCE_PAGE_ID_OR_TITLE_BINDING_FAILED"]
        decisions.append(make_decision(
            lane="legilist_source_binding",
            candidate_id=candidate_id,
            person_id=person_id,
            display_name=evidence.get("display_name"),
            decision=disposition,
            rationale_codes=reasons,
            evidence=evidence,
        ))
        review_material[candidate_id] = evidence

    covered_decisions: list[dict[str, Any]] = []
    for row in covered_rows:
        person_id = str(row["lda_source_person_id"])
        candidate_id = str(row["claim_id"])
        episode = None
        if row.get("explicit_no_position"):
            disposition = "REJECTED"
            reasons = ["EXPLICIT_NO_COVERED_POSITION"]
        elif (
            (clean := clean_covered_candidate(row)) is not None
            and bounds_within_cutoff(clean[0], as_of_date)
            and clean_role_and_employer(clean[1], clean[2])
        ):
            bounds, title, employer = clean
            disposition = "PROVISIONALLY_ACCEPTED"
            reasons = [
                "SOURCE_NATIVE_LDA_IDENTITY",
                "ONE_HIGH_CONFIDENCE_ROLE_AND_CONTAINER",
                "ONE_CLEAN_CLOSED_DATE_RANGE",
                "PENDING_COVERED_POSITION_GOLD_CALIBRATION",
            ]
            episode = make_episode(
                lane="lda_covered_position_parse",
                candidate_id=candidate_id,
                person_id=person_id,
                display_name=people.get(person_id, {}).get("display_name"),
                employer=employer,
                title=title,
                bounds=bounds,
                urls=[],
                source_as_of=as_of,
                identity_status="SOURCE_NATIVE_ACCEPTED",
                blockers=[
                    "COVERED_POSITION_PARSER_GOLD_REQUIRED",
                    "CONTAINER_NORMALIZATION_REQUIRED",
                    "FABLE_OPUS_REVIEW_REQUIRED",
                ],
                temporal_semantics="ASSERTED_EPISODE",
            )
            episodes.append(episode)
        else:
            disposition = "REVIEW_REQUIRED"
            reasons = ["COVERED_POSITION_PARSE_AMBIGUOUS_UNBOUNDED_OR_OUTSIDE_CUTOFF"]
        decision = make_decision(
            lane="lda_covered_position_parse",
            candidate_id=candidate_id,
            person_id=person_id,
            display_name=people.get(person_id, {}).get("display_name"),
            decision=disposition,
            rationale_codes=reasons,
            evidence=row,
            proposed_episode_id=episode["episode_id"] if episode else None,
        )
        decisions.append(decision)
        if episode is not None:
            episode["decision_ids"] = [decision["decision_id"]]
        covered_decisions.append(decision)
        review_material[candidate_id] = dict(row)

    registrant_count = 0
    for row in rows(registrant_associations):
        registrant_count += 1
        person_id = str(row["lda_source_person_id"])
        candidate_id = str(row["episode_id"])
        decisions.append(make_decision(
            lane="lda_registrant_association",
            candidate_id=candidate_id,
            person_id=person_id,
            display_name=row.get("display_name"),
            decision="ACCEPTED_SOURCE_NATIVE_ASSOCIATION",
            rationale_codes=[
                "SOURCE_NATIVE_LDA_PERSON_AND_REGISTRANT_IDS",
                "FILING_ACTIVITY_OBSERVATION_NOT_EMPLOYMENT_CONTINUITY",
            ],
            evidence=row,
        ))

    structured_decisions: list[dict[str, Any]] = []
    for profile in rows(structured_profiles):
        person_id = str(profile["lda_source_person_id"])
        person_gate = structured_person_gate(profile, captures)
        for ordinal, raw_episode in enumerate(profile.get("employment_episodes") or [], start=1):
            candidate_id = "structured-profile-episode:" + digest({
                "person": person_id, "ordinal": ordinal, "episode": raw_episode,
                "source_shard": profile.get("source_shard"),
            })
            gate = structured_episode_gate(raw_episode, captures, as_of_date) if person_gate else None
            episode = None
            if gate is not None:
                bounds, urls = gate
                disposition = "PROVISIONALLY_ACCEPTED"
                reasons = [
                    "VERY_HIGH_MULTI_SOURCE_IDENTITY_CANDIDATE",
                    "CAPTURED_MULTI_SOURCE_OR_OFFICIAL_EPISODE_SUPPORT",
                    "STRUCTURED_EMPLOYER_TITLE_AND_DATES",
                    "PENDING_IDENTITY_GOLD_AND_FABLE_REVIEW",
                ]
                episode = make_episode(
                    lane="structured_public_profile_episode",
                    candidate_id=candidate_id,
                    person_id=person_id,
                    display_name=profile.get("display_name"),
                    employer=str(raw_episode["employer"]),
                    title=str(raw_episode["title"]),
                    bounds=bounds,
                    urls=urls,
                    source_as_of=as_of,
                    identity_status="PROVISIONALLY_ACCEPTED_MULTI_SOURCE",
                    blockers=[
                        "IDENTITY_GOLD_CALIBRATION_REQUIRED",
                        "CONTAINER_NORMALIZATION_REQUIRED",
                        "FABLE_OPUS_REVIEW_REQUIRED",
                    ],
                    temporal_semantics="ASSERTED_EPISODE",
                )
                episodes.append(episode)
            else:
                disposition = "REVIEW_REQUIRED"
                reasons = ["STRUCTURED_EPISODE_FAILED_STRICT_IDENTITY_OR_SUPPORT_GATE"]
            decision = make_decision(
                lane="structured_public_profile_episode",
                candidate_id=candidate_id,
                person_id=person_id,
                display_name=profile.get("display_name"),
                decision=disposition,
                rationale_codes=reasons,
                evidence=raw_episode,
                proposed_episode_id=episode["episode_id"] if episode else None,
            )
            decisions.append(decision)
            if episode is not None:
                episode["decision_ids"] = [decision["decision_id"]]
            structured_decisions.append(decision)
            review_material[candidate_id] = {
                "profile_identity_support": profile.get("identity_support") or [],
                "profile_gaps": profile.get("gaps") or [],
                "episode": raw_episode,
            }

    house_rows = list(rows(house_payroll))
    house_candidates: defaultdict[str, set[str]] = defaultdict(set)
    for row in house_rows:
        house_candidates[str(row["payroll_candidate_id"])].add(str(row["lda_source_person_id"]))
    identity_decisions: list[dict[str, Any]] = []
    for row in house_rows:
        person_id = str(row["lda_source_person_id"])
        candidate_id = str(row["candidate_match_id"])
        claim = corroborating_claim(
            row, support_index,
            title_key="title_description_raw", organization_key="employing_office_raw",
        )
        unique = len(house_candidates[str(row["payroll_candidate_id"])]) == 1
        bounded = (
            row.get("service_date_report_period_relationship") == "SERVICE_RANGE_WITHIN_REPORT_PERIOD"
            and row.get("service_start_date_candidate_iso")
            and row.get("service_end_date_candidate_iso")
        )
        episode = None
        quality = clean_role_and_employer(
            row.get("title_description_raw"), row.get("employing_office_raw")
        )
        if unique and bounded and claim is not None and quality:
            start = date.fromisoformat(str(row["service_start_date_candidate_iso"]))
            end = date.fromisoformat(str(row["service_end_date_candidate_iso"])) + timedelta(days=1)
            bounds = {
                "valid_start_earliest": start.isoformat(),
                "valid_start_latest": start.isoformat(),
                "valid_end_earliest": end.isoformat(),
                "valid_end_latest": end.isoformat(),
                "start_precision": "day",
                "end_precision": "day",
                "asserted_current": False,
            }
            disposition = "PROVISIONALLY_ACCEPTED"
            reasons = [
                "UNIQUE_PAYROLL_TO_LDA_NAME_CANDIDATE",
                "OFFICIAL_HOUSE_PAYROLL_BOUNDED_OBSERVATION",
                "INDEPENDENT_LDA_ROLE_AND_OFFICE_CORROBORATION",
                "PENDING_IDENTITY_GOLD_CALIBRATION",
            ]
            episode = make_episode(
                lane="house_payroll_corroborated",
                candidate_id=candidate_id,
                person_id=person_id,
                display_name=row.get("lda_display_name"),
                employer=str(row["employing_office_raw"]),
                title=str(row["title_description_raw"]),
                bounds=bounds,
                urls=source_urls(row),
                source_as_of=as_of,
                identity_status="PROVISIONALLY_ACCEPTED_CORROBORATED",
                blockers=[
                    "IDENTITY_GOLD_CALIBRATION_REQUIRED",
                    "CONTAINER_NORMALIZATION_REQUIRED",
                    "FABLE_OPUS_REVIEW_REQUIRED",
                ],
                temporal_semantics="OBSERVATION_ONLY",
                observation_intervals=[{
                    "basis": "OFFICIAL_SERVICE_RANGE",
                    "start": start.isoformat(),
                    "end_exclusive": end.isoformat(),
                }],
                support_candidate_ids=[candidate_id, claim[0]],
            )
            episodes.append(episode)
        else:
            disposition = "REVIEW_REQUIRED"
            reasons = ["HOUSE_PAYROLL_NAME_MATCH_NOT_STRICTLY_CORROBORATED_OR_CLEAN"]
        decision = make_decision(
            lane="house_payroll_corroborated",
            candidate_id=candidate_id,
            person_id=person_id,
            display_name=row.get("lda_display_name"),
            decision=disposition,
            rationale_codes=reasons,
            evidence=row,
            proposed_episode_id=episode["episode_id"] if episode else None,
        )
        decisions.append(decision)
        if episode is not None:
            episode["decision_ids"] = [decision["decision_id"]]
        identity_decisions.append(decision)
        review_material[candidate_id] = {
            "source_candidate": dict(row),
            "unique_payroll_to_lda_name_candidate": unique,
            "queue_candidate_count_for_payroll_name": len(
                house_candidates[str(row["payroll_candidate_id"])]
            ),
            "bounded_official_service_range": bool(bounded),
            "role_and_employer_quality_gate": quality,
            "corroboration": None if claim is None else {
                "lda_claim": covered_by_claim.get(claim[0]),
                "title_similarity": claim[1],
                "organization_similarity": claim[2],
                "title_threshold": 0.34,
                "organization_threshold": 0.20,
            },
        }

    senate_count = 0
    for row in rows(senate_payroll):
        senate_count += 1
        person_id = str(row["lda_source_person_id"])
        candidate_id = str(row["match_candidate_id"])
        claim = corroborating_claim(
            row, support_index,
            title_key="title_candidate", organization_key="employing_office_candidate",
        )
        intervals = row.get("observed_report_intervals") or []
        bounded = len(intervals) == 1 and all(
            item.get("start") and item.get("end")
            and item.get("basis") != "COMPLEX_QUALIFIER_REVIEW_REQUIRED"
            for item in intervals
        )
        unique = row.get("queue_candidate_count_for_name") == 1
        quality = clean_role_and_employer(
            row.get("title_candidate"), row.get("employing_office_candidate")
        )
        episode = None
        if unique and bounded and claim is not None and quality:
            observed = intervals[0]
            starts = [date.fromisoformat(str(observed["start"]))]
            ends = [date.fromisoformat(str(observed["end"])) + timedelta(days=1)]
            bounds = {
                "valid_start_earliest": min(starts).isoformat(),
                "valid_start_latest": min(starts).isoformat(),
                "valid_end_earliest": max(ends).isoformat(),
                "valid_end_latest": max(ends).isoformat(),
                "start_precision": "day",
                "end_precision": "day",
                "asserted_current": False,
            }
            disposition = "PROVISIONALLY_ACCEPTED"
            reasons = [
                "UNIQUE_PAYROLL_TO_LDA_NAME_CANDIDATE",
                "OFFICIAL_SENATE_PAYROLL_BOUNDED_OBSERVATION",
                "INDEPENDENT_LDA_ROLE_AND_OFFICE_CORROBORATION",
                "SINGLE_PAYROLL_INTERVAL_IS_OBSERVATION_ONLY_NOT_CONTINUITY",
                "PENDING_IDENTITY_GOLD_CALIBRATION",
            ]
            episode = make_episode(
                lane="senate_payroll_corroborated",
                candidate_id=candidate_id,
                person_id=person_id,
                display_name=row.get("display_name"),
                employer=str(row["employing_office_candidate"]),
                title=str(row["title_candidate"]),
                bounds=bounds,
                urls=source_urls(row),
                source_as_of=as_of,
                identity_status="PROVISIONALLY_ACCEPTED_CORROBORATED",
                blockers=[
                    "IDENTITY_GOLD_CALIBRATION_REQUIRED",
                    "CONTAINER_NORMALIZATION_REQUIRED",
                    "FABLE_OPUS_REVIEW_REQUIRED",
                ],
                temporal_semantics="OBSERVATION_ONLY",
                observation_intervals=[{
                    "basis": str(observed.get("basis") or "UNKNOWN"),
                    "start": starts[0].isoformat(),
                    "end_exclusive": ends[0].isoformat(),
                }],
                support_candidate_ids=[candidate_id, claim[0]],
            )
            episodes.append(episode)
        else:
            disposition = "REVIEW_REQUIRED"
            reasons = [
                "SENATE_PAYROLL_NAME_MATCH_NOT_STRICTLY_CORROBORATED_OR_CLEAN",
                "MULTIPLE_OR_REVIEW_MARKED_OBSERVATION_INTERVALS_REQUIRE_SPLIT",
            ]
        decision = make_decision(
            lane="senate_payroll_corroborated",
            candidate_id=candidate_id,
            person_id=person_id,
            display_name=row.get("display_name"),
            decision=disposition,
            rationale_codes=reasons,
            evidence=row,
            proposed_episode_id=episode["episode_id"] if episode else None,
        )
        decisions.append(decision)
        if episode is not None:
            episode["decision_ids"] = [decision["decision_id"]]
        identity_decisions.append(decision)
        review_material[candidate_id] = {
            "source_candidate": dict(row),
            "unique_payroll_to_lda_name_candidate": unique,
            "queue_candidate_count_for_name": row.get("queue_candidate_count_for_name"),
            "single_clean_observation_interval": bool(bounded),
            "role_and_employer_quality_gate": quality,
            "corroboration": None if claim is None else {
                "lda_claim": covered_by_claim.get(claim[0]),
                "title_similarity": claim[1],
                "organization_similarity": claim[2],
                "title_threshold": 0.34,
                "organization_threshold": 0.20,
            },
        }

    decisions.sort(key=lambda row: row["decision_id"])
    if len({row["decision_id"] for row in decisions}) != len(decisions):
        raise AdjudicationError("duplicate adjudication decision IDs")
    provisional_support_decision_rows = len(episodes)
    episodes = consolidate_episodes(episodes)
    if len({row["episode_id"] for row in episodes}) != len(episodes):
        raise AdjudicationError("duplicate provisional episode IDs")

    person_decisions: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in decisions:
        person_decisions[row["lda_source_person_id"]][
            f"{row['lane']}:{row['decision']}"
        ] += 1
    person_episodes: Counter[str] = Counter(
        row["lda_source_person_id"] for row in episodes
    )
    person_episode_ids: defaultdict[str, list[str]] = defaultdict(list)
    for row in episodes:
        person_episode_ids[row["lda_source_person_id"]].append(row["episode_id"])
    person_decision_ids: defaultdict[str, list[str]] = defaultdict(list)
    for row in decisions:
        person_decision_ids[row["lda_source_person_id"]].append(row["decision_id"])
    open_gates = [
        "COVERED_POSITION_PARSER_PRECISION_GOLD_100_REQUIRED",
        "IDENTITY_PRECISION_RECALL_GOLD_200_REQUIRED",
        "CONTAINER_ADJUDICATION_REQUIRED",
        "SENATE_TEMPORAL_OBSERVATION_AUDIT_REQUIRED",
        "FABLE_OPUS_5_ADVERSARIAL_PASS_REQUIRED",
    ]
    summaries = []
    for person_id, person in sorted(
        people.items(), key=lambda item: (item[1]["sealed_queue_ordinal"], item[0])
    ):
        counts = dict(sorted(person_decisions.get(person_id, Counter()).items()))
        provisional_count = person_episodes[person_id]
        state = (
            "PROVISIONAL_EPISODES_PENDING_REVIEW" if provisional_count
            else "CANDIDATES_REVIEW_REQUIRED" if counts
            else "NO_CANDIDATES"
        )
        summaries.append({
            "schema_id": PERSON_SCHEMA,
            "lda_source_person_id": person_id,
            "display_name": person["display_name"],
            "sealed_queue_ordinal": person["sealed_queue_ordinal"],
            "adjudication_state": state,
            "decision_counts": counts,
            "provisional_episode_count": provisional_count,
            "final_episode_count": 0,
            "source_native_identity_status": "ACCEPTED",
            "cross_source_identity_merge_performed": False,
            "canonical_employment_promoted_count": 0,
            "primary_temporal_eligible_episode_count": 0,
            "complete_lifetime_employment_asserted": False,
            "open_gate_codes": open_gates,
            "decision_digest": digest(sorted(person_decision_ids.get(person_id, []))),
            "episode_digest": digest(sorted(person_episode_ids.get(person_id, []))),
        })

    covered_sample = deterministic_sample(
        covered_decisions,
        {"PROVISIONALLY_ACCEPTED": 50, "REVIEW_REQUIRED": 40, "REJECTED": 10},
        sample_kind="COVERED_POSITION_PARSER",
    )
    identity_sample = deterministic_stratified_sample(
        identity_decisions + structured_decisions,
        {
            ("house_payroll_corroborated", "PROVISIONALLY_ACCEPTED"): 60,
            ("senate_payroll_corroborated", "PROVISIONALLY_ACCEPTED"): 30,
            ("structured_public_profile_episode", "PROVISIONALLY_ACCEPTED"): 10,
            ("house_payroll_corroborated", "REVIEW_REQUIRED"): 60,
            ("senate_payroll_corroborated", "REVIEW_REQUIRED"): 30,
            ("structured_public_profile_episode", "REVIEW_REQUIRED"): 10,
        },
        sample_kind="IDENTITY_RULE",
    )
    episode_by_id = {row["episode_id"]: row for row in episodes}
    decision_by_id = {row["decision_id"]: row for row in decisions}
    for row in covered_sample + identity_sample:
        row["candidate_evidence"] = review_material[row["candidate_id"]]
        decision = decision_by_id[row["decision_id"]]
        row["proposed_episode"] = episode_by_id.get(decision.get("proposed_episode_id"))
        row["candidate_evidence_sha256"] = digest(row["candidate_evidence"])
        row["proposed_episode_sha256"] = (
            digest(row["proposed_episode"]) if row["proposed_episode"] is not None else None
        )
        sample_core = {
            key: value for key, value in row.items()
            if key not in {"candidate_evidence", "proposed_episode"}
        }
        row["sample_id"] = "adjudication:gold-sample:" + digest(sample_core)

    schemas = {
        schema_id: json.loads((SCHEMA_DIRECTORY / filename).read_text(encoding="utf-8"))
        for schema_id, filename in SCHEMA_FILES.items()
    }
    for schema in schemas.values():
        validate_schema_definition(schema)
    for row in decisions:
        validate_instance(row, schemas[DECISION_SCHEMA], _schema_checked=True)
    for row in episodes:
        validate_instance(row, schemas[EPISODE_SCHEMA], _schema_checked=True)
    for row in summaries:
        validate_instance(row, schemas[PERSON_SCHEMA], _schema_checked=True)
    for row in covered_sample + identity_sample:
        validate_instance(row, schemas[GOLD_SCHEMA], _schema_checked=True)

    decisions_path = output_root / "candidate_adjudication_decisions.ndjson.gz"
    episodes_path = output_root / "provisional_employment_episodes.ndjson.gz"
    summaries_path = output_root / "employment_adjudication_person_summary_25340.ndjson.gz"
    covered_sample_path = output_root / "covered_position_parser_gold_sample_100.ndjson.gz"
    identity_sample_path = output_root / "identity_rule_gold_sample_200.ndjson.gz"
    decision_rows, _ = write_gzip(decisions_path, decisions)
    episode_rows, _ = write_gzip(episodes_path, episodes)
    summary_rows, _ = write_gzip(summaries_path, summaries)
    covered_sample_rows, _ = write_gzip(covered_sample_path, covered_sample)
    identity_sample_rows, _ = write_gzip(identity_sample_path, identity_sample)

    lane_status_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in decisions:
        lane_status_counts[row["lane"]][row["decision"]] += 1
    episode_lane_counts = Counter(row["decision_id"].split(":", 2)[0] for row in [])
    del episode_lane_counts  # lane counts are derived through decision joins below
    provisional_by_lane: Counter[str] = Counter()
    for row in episodes:
        provisional_by_lane.update(row["evidence_lanes"])
    input_entries = {
        "sealed_queue": sealed_queue,
        "bulk_receipt": bulk_receipt,
        "covered_positions": covered_positions,
        "registrant_associations": registrant_associations,
        "structured_profiles": structured_profiles,
        "capture_ledger": capture_ledger,
        "house_payroll": house_payroll,
        "senate_payroll": senate_payroll,
    }
    input_entries.update(bulk_shard_inputs)
    fact_ledger = bulk.get("fact_ledger") or {}
    fact_ledger_path = Path(str(fact_ledger.get("path") or ""))
    if (
        not fact_ledger_path.is_file()
        or sha256(fact_ledger_path) != fact_ledger.get("sha256")
    ):
        raise AdjudicationError("bulk fact-ledger receipt binding failed")
    input_entries["bulk_fact_ledger"] = fact_ledger_path
    receipt = {
        "schema_id": RECEIPT_SCHEMA,
        "status": "GENERATION_VALID_REVIEW_OPEN",
        "method_version": METHOD_VERSION,
        "implementation": {
            "generator_path": str(Path(__file__).resolve()),
            "generator_sha256": sha256(Path(__file__).resolve()),
            "python_version": sys.version.split()[0],
        },
        "as_of": as_of,
        "sealed_scope_people": len(people),
        "source_native_identity_acceptances": len(people),
        "cross_source_identity_merges": 0,
        "decision_rows": decision_rows,
        "decision_status_counts": dict(sorted(Counter(row["decision"] for row in decisions).items())),
        "lane_status_counts": {
            lane: dict(sorted(counts.items())) for lane, counts in sorted(lane_status_counts.items())
        },
        "provisional_episode_rows": episode_rows,
        "provisional_support_decision_rows": provisional_support_decision_rows,
        "exact_fact_duplicate_rows_collapsed": provisional_support_decision_rows - episode_rows,
        "provisional_episode_lane_counts": dict(sorted(provisional_by_lane.items())),
        "temporal_semantics_counts": dict(sorted(Counter(
            row["temporal_semantics"] for row in episodes
        ).items())),
        "person_summary_rows": summary_rows,
        "bulk_candidate_rows_conserved": bulk_seen,
        "covered_position_rows_conserved": len(covered_rows),
        "registrant_association_rows_conserved": registrant_count,
        "structured_profile_rows": sum(1 for _ in rows(structured_profiles)),
        "house_payroll_rows_conserved": len(house_rows),
        "senate_payroll_rows_conserved": senate_count,
        "gold_samples": {
            "covered_position_parser": covered_sample_rows,
            "identity_rule": identity_sample_rows,
        },
        "canonical_employment_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "primary_temporal_eligible_episodes": 0,
        "open_gates": open_gates,
        "gate_states": {code: "OPEN" for code in open_gates},
        "inputs": {
            name: {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(input_entries.items())
        },
        "files": [
            file_entry(decisions_path, "candidate_adjudication_decisions", decision_rows,
                       DECISION_SCHEMA, SCHEMA_DIRECTORY / SCHEMA_FILES[DECISION_SCHEMA]),
            file_entry(episodes_path, "provisional_employment_episodes", episode_rows,
                       EPISODE_SCHEMA, SCHEMA_DIRECTORY / SCHEMA_FILES[EPISODE_SCHEMA]),
            file_entry(summaries_path, "person_summary", summary_rows,
                       PERSON_SCHEMA, SCHEMA_DIRECTORY / SCHEMA_FILES[PERSON_SCHEMA]),
            file_entry(covered_sample_path, "covered_position_gold_sample", covered_sample_rows,
                       GOLD_SCHEMA, SCHEMA_DIRECTORY / SCHEMA_FILES[GOLD_SCHEMA]),
            file_entry(identity_sample_path, "identity_rule_gold_sample", identity_sample_rows,
                       GOLD_SCHEMA, SCHEMA_DIRECTORY / SCHEMA_FILES[GOLD_SCHEMA]),
        ],
        "schemas": [
            {
                "schema_id": schema_id,
                "path": str(SCHEMA_DIRECTORY / filename),
                "sha256": sha256(SCHEMA_DIRECTORY / filename),
            }
            for schema_id, filename in sorted(SCHEMA_FILES.items())
        ],
    }
    validate_instance(receipt, schemas[RECEIPT_SCHEMA], _schema_checked=True)
    receipt_path = output_root / "employment_adjudication_receipt.json"
    receipt_path.write_bytes(compact(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sealed-queue", required=True, type=Path)
    parser.add_argument("--bulk-receipt", required=True, type=Path)
    parser.add_argument("--covered-positions", required=True, type=Path)
    parser.add_argument("--registrant-associations", required=True, type=Path)
    parser.add_argument("--structured-profiles", required=True, type=Path)
    parser.add_argument("--capture-ledger", required=True, type=Path)
    parser.add_argument("--house-payroll", required=True, type=Path)
    parser.add_argument("--senate-payroll", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    receipt = adjudicate(
        sealed_queue=args.sealed_queue.resolve(),
        bulk_receipt=args.bulk_receipt.resolve(),
        covered_positions=args.covered_positions.resolve(),
        registrant_associations=args.registrant_associations.resolve(),
        structured_profiles=args.structured_profiles.resolve(),
        capture_ledger=args.capture_ledger.resolve(),
        house_payroll=args.house_payroll.resolve(),
        senate_payroll=args.senate_payroll.resolve(),
        output_root=args.output_root.resolve(),
        as_of=args.as_of,
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
