#!/usr/bin/env python3
"""Validate and summarize the authenticated Politico profile crawl.

This deliberately does not handle authentication.  The signed-in browser writes
profile records; this program performs deterministic local ingestion, coverage,
privacy, and integrity checks without browser state or credentials.

A clean partial checkpoint is ``IN_PROGRESS`` and exits zero so collection can
continue.  ``--require-complete`` turns any unmet terminal requirement into exit
code 2; only the exact sealed 18,618-profile, zero-failure closure is ``PASS``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable



try:
    from .politico_completion_contract import completion_accepted, validate_browser_exception, SOURCE_EXCEPTION_POLICY
except ImportError:
    from politico_completion_contract import completion_accepted, validate_browser_exception, SOURCE_EXCEPTION_POLICY

COMMITTEE_ROLE = re.compile(
    r"\bfor\s+((?:House|Senate)\s+.*(?:Committee|Commission).*)$", re.I
)
CONTACT_KEYS = {
    "address",
    "cell",
    "contact",
    "email",
    "fax",
    "phone",
    "telephone",
}
EXPECTED_CORPUS_TOTAL = 18_618
PROFILE_URL_PREFIX = "https://directory.politicopro.com/congress/staffer/"
LEGACY_REQUESTS_PER_MINUTE = 40
AUTHORIZED_RAMP_REQUESTS_PER_MINUTE = {60, 80, 100, 120, 150, 200, 250}
AUTHORIZED_RAMP_MODE = "AUTHORIZED_GENTLE_RAMP"
LAST_BATCH_COUNTERS = (
    "attempted",
    "succeeded",
    "retryable_failures",
    "hard_failures",
)
ALLOWED_IDENTITY_STATUSES = {
    "",
    "UUID_AND_NAME_MATCH",
    "LIVE_NAME_CHANGED_SAME_UUID",
    "PROFILE_UNAVAILABLE_404",
}
PROFILE_NATIVE_COLLECTIONS = (
    "current_header_positions",
    "explicit_side_labels",
    "profile_issue_areas",
    "employment_history",
    "education",
)
COLLECTION_FIELDS = (
    "source_card_roles",
    "source_card_issue_areas",
    *PROFILE_NATIVE_COLLECTIONS,
)


def input_sha256(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_ndjson(path: Path, *, optional: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    if optional and not path.exists():
        return [], []
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, 1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise TypeError("record is not a JSON object")
                    rows.append(value)
                except (json.JSONDecodeError, TypeError) as exc:
                    errors.append(f"{path.name}:{line_number}: {exc}")
    except OSError as exc:
        errors.append(f"{path}: {exc}")
    return rows, errors


def duplicate_values(values: Iterable[Any]) -> list[str]:
    counts = Counter(str(value) for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def forbidden_contact_paths(value: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            normalized = re.sub(r"[^a-z]", "", str(key).lower())
            if normalized in CONTACT_KEYS or any(
                normalized.startswith(item) or normalized.endswith(item)
                for item in CONTACT_KEYS
            ):
                # The explicit false audit flag is required and is not contact data.
                if key != "contact_fields_collected":
                    hits.append(path)
            hits.extend(forbidden_contact_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(forbidden_contact_paths(child, f"{prefix}[{index}]"))
    return hits


def pct(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 4) if denominator else 0.0


def evidence_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def validate_api_source(row, evidence_by_hash):
    """Source omissions are valid observations only with bound, matching API data.

    This does not make them pass the full-content terminal completion gate.
    """
    raw=evidence_by_hash.get(row.get('projected_api_sha256'))
    uuid=str(row.get('profile_uuid',''))
    expected_url='https://directory.politicopro.com/proxy/lava/api/v1/person/'+uuid
    if not raw or raw.get('status')!=200 or raw.get('url')!=expected_url or row.get('source_api_url')!=expected_url:
        return False
    data=raw.get('data',{})
    if data.get('lexiconId')!=uuid and not (uuid.isdigit() and str(data.get('id'))==uuid and not data.get('lexiconId')):
        return False
    if row.get('verified_name') != (data.get('name',{}).get('displayName') or data.get('name',{}).get('full')):
        return False
    missing=[field for field in ('current_header_positions','employment_history') if not row.get(field)]
    if missing:
        if row.get('content_status')!='SOURCE_CONFIRMED_MISSING_FIELDS' or row.get('source_missing_collections')!=missing:
            return False
        if ('current_header_positions' in missing and data.get('stafferPositions')) or ('employment_history' in missing and data.get('employmentItems')):
            return False
    return True


def validate_api_404(row, observations_by_hash):
    raw=observations_by_hash.get(row.get('api_observation_sha256'))
    uuid=str(row.get('profile_uuid',''))
    expected_url='https://directory.politicopro.com/proxy/lava/api/v1/person/'+uuid
    return bool(raw and raw.get('profile_uuid')==uuid and raw.get('status')==404
                and raw.get('source_api_url')==expected_url and row.get('source_api_url')==expected_url
                and row.get('profile_api_status')==404 and row.get('observed_at')==raw.get('observed_at'))


def is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_rate_control(state: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    """Validate the fixed-40 or explicitly authorized gentle-ramp state contract."""

    errors: list[str] = []
    maximum = state.get("max_requests_per_minute")
    rate_control = state.get("rate_control")
    summary: dict[str, Any] = {
        "legacy_requests_per_minute": LEGACY_REQUESTS_PER_MINUTE,
        "authorized_ramp_values": sorted(AUTHORIZED_RAMP_REQUESTS_PER_MINUTE),
        "hard_ceiling": max(AUTHORIZED_RAMP_REQUESTS_PER_MINUTE),
        "max_requests_per_minute": maximum,
        "mode": rate_control.get("mode") if isinstance(rate_control, dict) else None,
        "current_requests_per_minute": (
            rate_control.get("current_requests_per_minute")
            if isinstance(rate_control, dict)
            else maximum if maximum == LEGACY_REQUESTS_PER_MINUTE else None
        ),
        "last_batch": (
            rate_control.get("last_batch")
            if isinstance(rate_control, dict)
            else None
        ),
    }

    if not is_nonnegative_int(maximum):
        errors.append(
            "max_requests_per_minute: expected a nonnegative integer, "
            f"got {maximum!r}"
        )
        summary["status"] = "FAIL"
        return errors, summary

    if maximum == LEGACY_REQUESTS_PER_MINUTE and rate_control is None:
        summary["contract"] = "LEGACY_FIXED_40"
        summary["status"] = "PASS"
        return errors, summary

    if (
        maximum != LEGACY_REQUESTS_PER_MINUTE
        and maximum not in AUTHORIZED_RAMP_REQUESTS_PER_MINUTE
    ):
        if maximum > max(AUTHORIZED_RAMP_REQUESTS_PER_MINUTE):
            errors.append(
                "max_requests_per_minute: "
                f"{maximum} exceeds the authorized hard ceiling of "
                f"{max(AUTHORIZED_RAMP_REQUESTS_PER_MINUTE)}"
            )
        else:
            errors.append(
                "max_requests_per_minute: expected legacy 40 or an authorized "
                f"ramp value in {sorted(AUTHORIZED_RAMP_REQUESTS_PER_MINUTE)}, "
                f"got {maximum}"
            )

    if not isinstance(rate_control, dict):
        errors.append(
            "rate_control: an object is required for every non-legacy rate"
        )
        summary["status"] = "FAIL"
        return errors, summary

    summary["contract"] = "AUTHORIZED_GENTLE_RAMP"
    if rate_control.get("mode") != AUTHORIZED_RAMP_MODE:
        errors.append(
            f"rate_control.mode: expected {AUTHORIZED_RAMP_MODE!r}, "
            f"got {rate_control.get('mode')!r}"
        )

    current = rate_control.get("current_requests_per_minute")
    if not is_nonnegative_int(current):
        errors.append(
            "rate_control.current_requests_per_minute: expected a nonnegative "
            f"integer, got {current!r}"
        )
    elif current != maximum:
        errors.append(
            "rate_control.current_requests_per_minute: expected it to equal "
            f"max_requests_per_minute ({maximum}), got {current}"
        )

    last_batch = rate_control.get("last_batch")
    valid_counters: dict[str, int] = {}
    if not isinstance(last_batch, dict):
        errors.append("rate_control.last_batch: expected an object")
    else:
        for key in LAST_BATCH_COUNTERS:
            value = last_batch.get(key)
            if not is_nonnegative_int(value):
                errors.append(
                    f"rate_control.last_batch.{key}: expected a nonnegative "
                    f"integer, got {value!r}"
                )
            else:
                valid_counters[key] = value
        if len(valid_counters) == len(LAST_BATCH_COUNTERS):
            outcomes = (
                valid_counters["succeeded"]
                + valid_counters["retryable_failures"]
                + valid_counters["hard_failures"]
            )
            if outcomes != valid_counters["attempted"]:
                errors.append(
                    "rate_control.last_batch: succeeded + retryable_failures + "
                    f"hard_failures must equal attempted; got {outcomes} != "
                    f"{valid_counters['attempted']}"
                )
            if valid_counters["hard_failures"] != 0:
                errors.append(
                    "rate_control.last_batch.hard_failures: continued authorized "
                    "ramp requires zero hard failures"
                )

    summary["status"] = "PASS" if not errors else "FAIL"
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--failures", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help=(
            "return nonzero unless the sealed 18,618-profile corpus satisfies "
            "every terminal completion requirement"
        ),
    )
    parser.add_argument("--source-exceptions", type=Path, help="Browser observations bound to API-confirmed source omissions")
    args = parser.parse_args()

    input_paths = {
        "directory": args.directory, "profiles": args.profiles,
        "failures": args.failures, "state": args.state,
    }
    if args.source_exceptions:
        input_paths["source_exceptions"] = args.source_exceptions
    api_evidence_path=args.profiles.parent/'api_projected_evidence_20260905.ndjson'
    api_observations_path=args.profiles.parent/'api_recheck_observations_20260905.ndjson'
    for name,path in [('api_projected_evidence',api_evidence_path),('api_observations',api_observations_path)]:
        if path.exists(): input_paths[name]=path
    input_hashes = {name: input_sha256(path) for name, path in input_paths.items()}
    profile_prefix_bytes = args.profiles.stat().st_size if args.profiles.exists() else 0

    directory_rows, directory_errors = read_ndjson(args.directory)
    profiles, profile_errors = read_ndjson(args.profiles)
    api_evidence,api_evidence_errors=read_ndjson(api_evidence_path,optional=True)
    api_observations,api_observation_errors=read_ndjson(api_observations_path,optional=True)
    api_evidence_by_hash={evidence_digest(r['data']):r for r in api_evidence if isinstance(r.get('data'),dict)}
    api_observations_by_hash={evidence_digest(r):r for r in api_observations}
    api_source_errors=api_evidence_errors+api_observation_errors
    source_incomplete_profiles=[]
    exception_rows, exception_errors = read_ndjson(args.source_exceptions) if args.source_exceptions else ([], [])
    exception_by_id = {r.get('profile_uuid'): r for r in exception_rows}
    exception_errors.extend('duplicate browser exception: ' + value for value in duplicate_values(r.get('profile_uuid') for r in exception_rows))
    accepted_source_exceptions = []
    failures, failure_errors = read_ndjson(args.failures, optional=True) if args.failures else ([], [])

    expected_by_id = {
        str(row.get("profile_uuid")): row
        for row in directory_rows
        if row.get("profile_uuid")
    }
    committee_ids = {
        profile_id
        for profile_id, row in expected_by_id.items()
        if any(COMMITTEE_ROLE.search(str(role)) for role in row.get("roles", []))
    }
    profile_ids = [str(row.get("profile_uuid", "")) for row in profiles]
    unique_profile_ids = set(filter(None, profile_ids))
    failure_profile_ids = [str(row.get("profile_uuid", "")) for row in failures]
    failed_ids = set(filter(None, failure_profile_ids))

    duplicate_profile_ids = duplicate_values(profile_ids)
    directory_duplicate_ids = duplicate_values(
        row.get("profile_uuid") for row in directory_rows
    )
    missing_profile_ids = [
        index + 1 for index, profile_id in enumerate(profile_ids) if not profile_id
    ]
    duplicate_failure_ids = duplicate_values(failure_profile_ids)
    missing_failure_ids = [
        index + 1
        for index, profile_id in enumerate(failure_profile_ids)
        if not profile_id
    ]
    unexpected_ids = sorted(unique_profile_ids - set(expected_by_id))
    unexpected_failure_ids = sorted(failed_ids - set(expected_by_id))
    success_failure_overlap = sorted(unique_profile_ids & failed_ids)
    name_mismatches: list[dict[str, str]] = []
    invalid_identity_exceptions: list[dict[str, str]] = []
    identity_exception_policy_violations: list[dict[str, Any]] = []
    missing_required_fields: list[dict[str, Any]] = []
    contact_violations: list[dict[str, Any]] = []
    malformed_collections: list[dict[str, Any]] = []
    malformed_collection_items: list[dict[str, Any]] = []
    source_url_mismatches: list[dict[str, Any]] = []
    incomplete_profile_content: list[dict[str, Any]] = []
    unavailable_404_rows: list[dict[str, Any]] = []
    renamed_same_uuid_rows: list[dict[str, Any]] = []

    required = (
        "profile_uuid",
        "expected_name",
        "verified_name",
        "partition",
        "source_card_roles",
        "source_card_issue_areas",
        "current_header_positions",
        "explicit_side_labels",
        "profile_issue_areas",
        "employment_history",
        "education",
        "observed_at",
        "source_url",
        "review_status",
        "contact_fields_collected",
    )
    for line_number, row in enumerate(profiles, 1):
        absent = [key for key in required if key not in row]
        if absent:
            missing_required_fields.append({"line": line_number, "fields": absent})
        profile_id = str(row.get("profile_uuid", ""))
        expected = expected_by_id.get(profile_id)
        sealed_name = str(expected.get("name", "")) if expected else ""
        expected_name = str(row.get("expected_name", ""))
        verified_name = str(row.get("verified_name", ""))
        identity_status = str(row.get("identity_status", ""))
        api_source_valid=False
        if row.get('extraction_method')=='AUTHENTICATED_PERSON_API_V1':
            api_source_valid=validate_api_source(row,api_evidence_by_hash)
            if not api_source_valid: api_source_errors.append(f'{profile_id}: invalid API source binding or missing-field declaration')
        exact_match = (
            expected
            and sealed_name == expected_name
            and expected_name == verified_name
            and identity_status in ("", "UUID_AND_NAME_MATCH")
        )
        renamed_same_uuid = (
            expected
            and sealed_name == expected_name
            and bool(verified_name)
            and expected_name != verified_name
            and identity_status == "LIVE_NAME_CHANGED_SAME_UUID"
        )
        unavailable_404 = (
            expected
            and sealed_name == expected_name
            and row.get("verified_name") is None
            and identity_status == "PROFILE_UNAVAILABLE_404"
            and not row.get("employment_history")
            and not row.get("education")
        )
        if not (exact_match or renamed_same_uuid or unavailable_404):
            name_mismatches.append(
                {
                    "profile_uuid": profile_id,
                    "sealed_name": sealed_name,
                    "expected_name": expected_name,
                    "verified_name": verified_name,
                }
            )
        if identity_status not in ALLOWED_IDENTITY_STATUSES:
            invalid_identity_exceptions.append(
                {"profile_uuid": profile_id, "identity_status": identity_status}
            )
        expected_source_url = f"{PROFILE_URL_PREFIX}{profile_id}"
        if row.get("source_url") != expected_source_url:
            source_url_mismatches.append(
                {
                    "line": line_number,
                    "profile_uuid": profile_id,
                    "expected": expected_source_url,
                    "actual": row.get("source_url"),
                }
            )
        if "observed_source_url" in row and row["observed_source_url"] != expected_source_url:
            source_url_mismatches.append(
                {
                    "line": line_number, "profile_uuid": profile_id,
                    "field": "observed_source_url", "expected": expected_source_url,
                    "actual": row["observed_source_url"],
                }
            )
        for field in COLLECTION_FIELDS:
            if field in row and not isinstance(row[field], list):
                malformed_collections.append(
                    {"line": line_number, "profile_uuid": profile_id, "field": field}
                )
        collection_contracts = {
            "employment_history": ("employer", "date_text", "title"),
            "education": ("institution", "date_text", "degree"),
        }
        for field, item_fields in collection_contracts.items():
            collection = row.get(field, [])
            if not isinstance(collection, list):
                continue
            for item_number, item in enumerate(collection, 1):
                if not isinstance(item, dict):
                    malformed_collection_items.append(
                        {
                            "line": line_number,
                            "profile_uuid": profile_id,
                            "field": field,
                            "item": item_number,
                            "error": "not an object",
                        }
                    )
                    continue
                missing_item_fields = [key for key in item_fields if key not in item]
                if missing_item_fields:
                    malformed_collection_items.append(
                        {
                            "line": line_number,
                            "profile_uuid": profile_id,
                            "field": field,
                            "item": item_number,
                            "missing_fields": missing_item_fields,
                        }
                    )
        if unavailable_404:
            unavailable_404_rows.append(
                {
                    "profile_uuid": profile_id,
                    "expected_name": expected_name,
                    "source_url": row.get("source_url"),
                    "review_status": row.get("review_status"),
                }
            )
            nonempty_profile_fields = [
                field for field in PROFILE_NATIVE_COLLECTIONS if row.get(field)
            ]
            evidence = row.get("unavailable_evidence")
            expected_http_status = {
                "HTTP_404": 404, "STABLE_SCOPED_ERROR_HEADING": 200,
            }.get(evidence) if isinstance(evidence, str) else None
            evidence_valid = (
                expected_http_status is not None
                and row.get("response_status") == expected_http_status
                and row.get("observed_source_url") == expected_source_url
                and (
                    evidence != "STABLE_SCOPED_ERROR_HEADING"
                    or row.get("profile_api_status") == 404
                )
            )
            if evidence=='PERSON_API_HTTP_404':
                evidence_valid=validate_api_404(row,api_observations_by_hash)
            if (
                row.get("review_status") != "IDENTITY_EXCEPTION_REVIEW_REQUIRED"
                or nonempty_profile_fields
                or not evidence_valid
            ):
                identity_exception_policy_violations.append(
                    {
                        "line": line_number,
                        "profile_uuid": profile_id,
                        "identity_status": identity_status,
                        "review_status": row.get("review_status"),
                        "nonempty_profile_fields": nonempty_profile_fields,
                        "unavailable_evidence_valid": evidence_valid,
                    }
                )
        elif renamed_same_uuid:
            renamed_same_uuid_rows.append(
                {
                    "profile_uuid": profile_id,
                    "expected_name": expected_name,
                    "verified_name": verified_name,
                    "source_url": row.get("source_url"),
                    "review_status": row.get("review_status"),
                }
            )
            if row.get("review_status") != "IDENTITY_EXCEPTION_REVIEW_REQUIRED":
                identity_exception_policy_violations.append(
                    {
                        "line": line_number,
                        "profile_uuid": profile_id,
                        "identity_status": identity_status,
                        "review_status": row.get("review_status"),
                    }
                )
        # A changed name requires review, not an exemption from rendered content.
        # Apply this to every non-404 row, including identity exceptions.
        if identity_status != "PROFILE_UNAVAILABLE_404":
            missing_content = [
                field
                for field in ("current_header_positions", "employment_history")
                if not row.get(field)
            ]
            if missing_content:
                if api_source_valid and row.get('content_status')=='SOURCE_CONFIRMED_MISSING_FIELDS':
                    source_incomplete_profiles.append({'profile_uuid':profile_id,'expected_name':expected_name,
                        'verified_name':row.get('verified_name'),'source_missing_collections':missing_content,
                        'source_api_url':row.get('source_api_url'),'projected_api_sha256':row.get('projected_api_sha256')})
                    observation = exception_by_id.get(profile_id)
                    if validate_browser_exception(row, observation):
                        accepted_source_exceptions.append(observation)
                    elif observation is not None:
                        exception_errors.append(profile_id + ': browser observation does not confirm this source omission')
                else:
                    incomplete_profile_content.append(
                    {
                        "line": line_number,
                        "profile_uuid": profile_id,
                        "missing_or_empty": missing_content,
                    }
                )
        paths = forbidden_contact_paths(row)
        if paths or row.get("contact_fields_collected") is not False:
            contact_violations.append(
                {
                    "line": line_number,
                    "profile_uuid": profile_id,
                    "paths": paths,
                    "contact_fields_collected": row.get("contact_fields_collected"),
                }
            )

    state: dict[str, Any] | None = None
    state_errors: list[str] = []
    if args.state:
        try:
            state_value = json.loads(args.state.read_text(encoding="utf-8"))
            if not isinstance(state_value, dict):
                raise TypeError("crawl state is not a JSON object")
            state = state_value
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            state_errors.append(str(exc))

    expected_ids = set(expected_by_id)
    all_completed = unique_profile_ids & expected_ids
    committee_completed = unique_profile_ids & committee_ids
    all_unresolved = expected_ids - unique_profile_ids - failed_ids
    committee_unresolved = committee_ids - unique_profile_ids - failed_ids
    employment_records = sum(
        len(row.get("employment_history", []))
        for row in profiles
        if isinstance(row.get("employment_history", []), list)
    )
    education_records = sum(
        len(row.get("education", []))
        for row in profiles
        if isinstance(row.get("education", []), list)
    )
    content_bearing_profiles = sum(
        1
        for row in profiles
        if row.get("identity_status") != "PROFILE_UNAVAILABLE_404"
        and bool(row.get("verified_name"))
        and bool(row.get("current_header_positions"))
        and bool(row.get("employment_history"))
    )
    profiles_with_employment_history = sum(
        1 for row in profiles if bool(row.get("employment_history"))
    )
    profiles_with_education = sum(1 for row in profiles if bool(row.get("education")))
    profiles_with_current_positions = sum(
        1 for row in profiles if bool(row.get("current_header_positions"))
    )
    current_position_records = sum(
        len(row.get("current_header_positions", []))
        for row in profiles
        if isinstance(row.get("current_header_positions", []), list)
    )
    explicit_side_label_records = sum(
        len(row.get("explicit_side_labels", []))
        for row in profiles
        if isinstance(row.get("explicit_side_labels", []), list)
    )
    profile_issue_area_records = sum(
        len(row.get("profile_issue_areas", []))
        for row in profiles
        if isinstance(row.get("profile_issue_areas", []), list)
    )

    state_contract_errors: list[str] = []
    if state is not None:
        expected_state_values = {
            "queue_total": len(expected_ids),
            "total_succeeded": len(all_completed),
            "total_failed": len(failed_ids & expected_ids),
            "remaining": len(all_unresolved),
        }
        for key, expected_value in expected_state_values.items():
            actual_value = state.get(key)
            if (
                isinstance(actual_value, bool)
                or not isinstance(actual_value, int)
                or actual_value != expected_value
            ):
                state_contract_errors.append(
                    f"{key}: expected {expected_value!r}, got {actual_value!r}"
                )
        if state.get("schema_id") != "politico-profile-crawl-state-v1":
            state_contract_errors.append(
                "schema_id: expected 'politico-profile-crawl-state-v1', "
                f"got {state.get('schema_id')!r}"
            )
        if state.get("scope") != "ALL_CURRENT_PROFILES":
            state_contract_errors.append(
                "scope: expected 'ALL_CURRENT_PROFILES', "
                f"got {state.get('scope')!r}"
            )
        if not isinstance(state.get("halted"), bool):
            state_contract_errors.append(
                f"halted: expected a boolean, got {state.get('halted')!r}"
            )
        rate_control_errors, rate_control_summary = validate_rate_control(state)
        state_contract_errors.extend(rate_control_errors)
    else:
        rate_control_summary = {
            "status": "NOT_AVAILABLE",
            "legacy_requests_per_minute": LEGACY_REQUESTS_PER_MINUTE,
            "authorized_ramp_values": sorted(AUTHORIZED_RAMP_REQUESTS_PER_MINUTE),
            "hard_ceiling": max(AUTHORIZED_RAMP_REQUESTS_PER_MINUTE),
        }

    sealed_directory_contract_errors: list[str] = []
    if len(directory_rows) != EXPECTED_CORPUS_TOTAL:
        sealed_directory_contract_errors.append(
            f"directory rows: expected {EXPECTED_CORPUS_TOTAL}, got {len(directory_rows)}"
        )
    if len(expected_ids) != EXPECTED_CORPUS_TOTAL:
        sealed_directory_contract_errors.append(
            "directory unique profiles: expected "
            f"{EXPECTED_CORPUS_TOTAL}, got {len(expected_ids)}"
        )

    omission_ids = {r['profile_uuid'] for r in source_incomplete_profiles}
    exception_errors.extend('unexpected browser exception: ' + str(value) for value in set(exception_by_id) - omission_ids)
    failures_found = {
        "ndjson_parse_errors": directory_errors + profile_errors + failure_errors,
        "api_source_evidence_errors": api_source_errors,
        "source_exception_evidence_errors": exception_errors,
        "directory_duplicate_profile_ids": directory_duplicate_ids,
        "profile_duplicate_profile_ids": duplicate_profile_ids,
        "failure_duplicate_profile_ids": duplicate_failure_ids,
        "profile_rows_without_id": missing_profile_ids,
        "failure_rows_without_id": missing_failure_ids,
        "unexpected_profile_ids": unexpected_ids,
        "unexpected_failure_profile_ids": unexpected_failure_ids,
        "success_failure_profile_overlap": success_failure_overlap,
        "name_mismatches": name_mismatches,
        "invalid_identity_exceptions": invalid_identity_exceptions,
        "identity_exception_policy_violations": identity_exception_policy_violations,
        "missing_required_fields": missing_required_fields,
        "malformed_collections": malformed_collections,
        "malformed_collection_items": malformed_collection_items,
        "source_url_mismatches": source_url_mismatches,
        "incomplete_profile_content": incomplete_profile_content,
        "contact_policy_violations": contact_violations,
        "state_errors": state_errors,
        "state_contract_errors": state_contract_errors,
        "sealed_directory_contract_errors": sealed_directory_contract_errors,
        "input_snapshot_changes": [
            name for name, path in input_paths.items()
            if input_sha256(path) != input_hashes[name]
        ],
    }
    hard_failure_count = sum(len(value) for value in failures_found.values())
    state_total_succeeded = state.get("total_succeeded") if state else None
    state_total_failed = state.get("total_failed") if state else None
    state_remaining = state.get("remaining") if state else None
    state_queue_total = state.get("queue_total") if state else None
    state_halted = state.get("halted") if state else None
    completion_checks = {
        "sealed_directory_rows": {
            "expected": EXPECTED_CORPUS_TOTAL,
            "actual": len(directory_rows),
            "pass": len(directory_rows) == EXPECTED_CORPUS_TOTAL,
        },
        "sealed_directory_unique_profiles": {
            "expected": EXPECTED_CORPUS_TOTAL,
            "actual": len(expected_ids),
            "pass": len(expected_ids) == EXPECTED_CORPUS_TOTAL,
        },
        "state_queue_total": {
            "expected": EXPECTED_CORPUS_TOTAL,
            "actual": state_queue_total,
            "pass": state_queue_total == EXPECTED_CORPUS_TOTAL,
        },
        "profile_rows": {
            "expected": EXPECTED_CORPUS_TOTAL,
            "actual": len(profiles),
            "pass": len(profiles) == EXPECTED_CORPUS_TOTAL,
        },
        "unique_profiles_collected": {
            "expected": EXPECTED_CORPUS_TOTAL,
            "actual": len(unique_profile_ids),
            "pass": len(unique_profile_ids) == EXPECTED_CORPUS_TOTAL,
        },
        "profiles_completed": {
            "expected": EXPECTED_CORPUS_TOTAL,
            "actual": len(all_completed),
            "pass": len(all_completed) == EXPECTED_CORPUS_TOTAL,
        },
        "state_total_succeeded": {
            "expected": EXPECTED_CORPUS_TOTAL,
            "actual": state_total_succeeded,
            "pass": state_total_succeeded == EXPECTED_CORPUS_TOTAL,
        },
        "profiles_accounted": {
            "expected": EXPECTED_CORPUS_TOTAL,
            "actual": len(all_completed) + len(failed_ids & expected_ids),
            "pass": (
                len(all_completed) + len(failed_ids & expected_ids)
                == EXPECTED_CORPUS_TOTAL
            ),
        },
        "unresolved_profiles": {
            "expected": 0,
            "actual": len(all_unresolved),
            "pass": len(all_unresolved) == 0,
        },
        "failure_rows": {
            "expected": 0,
            "actual": len(failures),
            "pass": len(failures) == 0,
        },
        "unique_failed_profiles": {
            "expected": 0,
            "actual": len(failed_ids),
            "pass": len(failed_ids) == 0,
        },
        "state_total_failed": {
            "expected": 0,
            "actual": state_total_failed,
            "pass": state_total_failed == 0,
        },
        "state_remaining": {
            "expected": 0,
            "actual": state_remaining,
            "pass": state_remaining == 0,
        },
        "state_halted": {
            "expected": False,
            "actual": state_halted,
            "pass": state_halted is False,
        },
        "rate_control_contract": {
            "expected": "PASS",
            "actual": rate_control_summary.get("status"),
            "pass": rate_control_summary.get("status") == "PASS",
        },
        "hard_verification_failures": {
            "expected": 0,
            "actual": hard_failure_count,
            "pass": hard_failure_count == 0,
        },
        "content_or_allowed_404_partition": {
            "expected": len(profiles),
            "actual": content_bearing_profiles + len(unavailable_404_rows) + len(accepted_source_exceptions),
            "pass": (
                content_bearing_profiles + len(unavailable_404_rows) + len(accepted_source_exceptions) == len(profiles)
            ),
        },
    }
    unmet_completion_requirements = [
        key for key, value in completion_checks.items() if not value["pass"]
    ]
    completion_ready = not unmet_completion_requirements
    integrity_status = "PASS" if hard_failure_count == 0 else "FAIL"
    status = (
        "FAIL"
        if hard_failure_count
        else "PASS"
        if completion_ready
        else "IN_PROGRESS"
    )
    receipt = {
        "schema_id": "politico-profile-crawl-verification-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "integrity_status": integrity_status,
        "completion_status": ("COMPLETE_WITH_EXCEPTIONS" if accepted_source_exceptions else "COMPLETE") if completion_ready else "INCOMPLETE",
        "source_exception_verification": {
            "status": "PASS" if not exception_errors and len(accepted_source_exceptions) == len(source_incomplete_profiles) else "INCOMPLETE",
            "policy": SOURCE_EXCEPTION_POLICY,
            "accepted_count": len(accepted_source_exceptions),
            "source_incomplete_count": len(source_incomplete_profiles),
            "evidence_sha256": input_hashes.get('source_exceptions'),
            "profile_prefix_sha256": input_hashes['profiles'],
            "rows": accepted_source_exceptions,
        },
        "acquisition_status": "ALL_DIRECTORY_RECORDS_ACCOUNTED" if len(all_completed)==EXPECTED_CORPUS_TOTAL and not hard_failure_count else "IN_PROGRESS",
        "source_incomplete_profiles": source_incomplete_profiles,
        "source_omission_policy": "Missing source collections remain distinct from populated content. Matching HTTP-200 API evidence plus a completed, exact-URL browser check permits COMPLETE_WITH_EXCEPTIONS. Rendered unavailable pages and rendered missing sections are recorded separately; failed retrievals never establish emptiness.",
        "inputs": {
            "directory": str(args.directory.resolve()),
            "profiles": str(args.profiles.resolve()),
            "failures": str(args.failures.resolve()) if args.failures else None,
            "state": str(args.state.resolve()) if args.state else None,
            **{name:str(path.resolve()) for name,path in input_paths.items() if name.startswith('api_') or name == 'source_exceptions'},
        },
        "input_sha256": input_hashes,
        "profile_prefix_bytes": profile_prefix_bytes,
        "profile_prefix_sha256": input_hashes["profiles"],
        "counts": {
            "sealed_directory_rows": len(directory_rows),
            "sealed_directory_unique_profiles": len(expected_ids),
            "sealed_committee_profiles": len(committee_ids),
            "profile_rows": len(profiles),
            "unique_profiles_collected": len(unique_profile_ids),
            "profiles_accounted": len(all_completed) + len(failed_ids & expected_ids),
            "hard_crawl_failures": len(failures),
            "unique_hard_crawl_failure_profiles": len(failed_ids),
            "content_bearing_profiles": content_bearing_profiles,
            "source_incomplete_profiles": len(source_incomplete_profiles),
            "accepted_source_exceptions": len(accepted_source_exceptions),
            "profiles_with_current_positions": profiles_with_current_positions,
            "current_position_records": current_position_records,
            "profiles_with_employment_history": profiles_with_employment_history,
            "employment_history_records": employment_records,
            "profiles_with_education": profiles_with_education,
            "education_records": education_records,
            "explicit_side_label_records": explicit_side_label_records,
            "profile_issue_area_records": profile_issue_area_records,
            "allowed_profile_unavailable_404": len(unavailable_404_rows),
            "same_uuid_name_changes": len(renamed_same_uuid_rows),
            "identity_statuses": dict(sorted(Counter(
                str(row.get("identity_status") or "LEGACY_EXACT_MATCH")
                for row in profiles
            ).items())),
        },
        "coverage": {
            "all_profiles": {
                "completed": len(all_completed),
                "expected": len(expected_ids),
                "percent": pct(len(all_completed), len(expected_ids)),
                "unresolved": len(all_unresolved),
            },
            "committee_profiles": {
                "completed": len(committee_completed),
                "expected": len(committee_ids),
                "percent": pct(len(committee_completed), len(committee_ids)),
                "unresolved": len(committee_unresolved),
            },
        },
        "identity_exceptions": {
            "profile_unavailable_404": {
                "policy": (
                    "Counted as a successful UUID-accounted profile only when the "
                    "sealed name and URL match, verified_name is null, profile-native "
                    "collections are empty, review is explicitly required, and the observed "
                    "URL plus HTTP/scoped-rendered-error evidence are valid; a soft404 "
                    "also requires an observed person-API 404 response."
                ),
                "count": len(unavailable_404_rows),
                "rows": sorted(
                    unavailable_404_rows,
                    key=lambda row: str(row.get("profile_uuid", "")),
                ),
            },
            "live_name_changed_same_uuid": {
                "policy": (
                    "Retained as the same UUID without an identity merge and marked "
                    "for explicit review."
                ),
                "count": len(renamed_same_uuid_rows),
                "rows": sorted(
                    renamed_same_uuid_rows,
                    key=lambda row: str(row.get("profile_uuid", "")),
                ),
            },
        },
        "crawl_state": state,
        "rate_control_contract": rate_control_summary,
        "completion_gate": {
            "required_profile_total": EXPECTED_CORPUS_TOTAL,
            "status": "PASS" if completion_ready else "INCOMPLETE",
            "checks": completion_checks,
            "unmet_requirements": unmet_completion_requirements,
            "unmet_requirement_count": len(unmet_completion_requirements),
        },
        "verification_failures": failures_found,
        "verification_failure_count": hard_failure_count,
    }

    payload = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)
    if hard_failure_count:
        return 1
    if args.require_complete and not completion_ready:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
