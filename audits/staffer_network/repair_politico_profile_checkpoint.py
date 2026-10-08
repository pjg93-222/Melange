#!/usr/bin/env python3
"""Repair a verifier-identified partial Politico crawl checkpoint.

Rows with incomplete rendered profile content are quarantined and removed so
the resumable crawler will fetch them again. Verified 404 exception rows are
kept but their profile-native collections are cleared, matching the verifier's
explicit UUID-accounting contract. --requeue-all-unavailable-404 instead removes
and preserves every 404 row for fresh collection. A current, hash-bound FAIL
receipt is mandatory. No identity inference or field fabrication is performed.

--requeue-source-incomplete is a separate, additive mode for the owner ruling of
2026-09-05: rows the API crawler declared SOURCE_CONFIRMED_MISSING_FIELDS are
quarantined and requeued so the browser path can re-render them. That mode binds
to an integrity-PASS, IN_PROGRESS receipt with zero verifier failures, because the
verifier files those rows under source_incomplete_profiles rather than as
failures. It leaves every other row, including 404 exceptions, untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SOURCE_INCOMPLETE_DECLARATION = "SOURCE_CONFIRMED_MISSING_FIELDS"
SOURCE_INCOMPLETE_REASON = "SOURCE_INCOMPLETE_BROWSER_REQUEUE"
OWNER_RULING = (
    "Owner ruling (Paul, 2026-09-05 12:40 ET): "
    '"Re-crawl the 18 through the browser path first" '
    "- leave the verifier's completion contract alone."
)

PROFILE_COLLECTIONS = (
    "current_header_positions",
    "explicit_side_labels",
    "profile_issue_areas",
    "employment_history",
    "education",
)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def read_ndjson(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"non-object NDJSON row at line {line_number}")
            rows.append(value)
    return rows


def ndjson_text(rows: list[dict]) -> str:
    return "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)


def target_ids(items: object, category: str) -> set[str]:
    if not isinstance(items, list):
        raise ValueError(f"invalid verifier target list: {category}")
    ids: list[str] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("profile_uuid"), str) or not item["profile_uuid"]:
            raise ValueError(f"invalid verifier target in {category}")
        ids.append(item["profile_uuid"])
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate verifier targets in {category}")
    return set(ids)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--quarantine", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument(
        "--requeue-all-unavailable-404", action="store_true",
        help="quarantine and requeue every unavailable-404 row, including currently valid exceptions",
    )
    parser.add_argument(
        "--requeue-source-incomplete", action="store_true",
        help="quarantine and requeue the verifier's declared source-incomplete rows for the browser path",
    )
    args = parser.parse_args(argv)
    if args.requeue_source_incomplete and args.requeue_all_unavailable_404:
        parser.error("--requeue-source-incomplete and --requeue-all-unavailable-404 are mutually exclusive")

    paths = [args.profiles, args.verification, args.state, args.quarantine, args.receipt]
    if len({os.path.normcase(str(path.resolve())) for path in paths}) != len(paths):
        raise ValueError("input and output paths must all be distinct")

    for output in (args.quarantine, args.receipt):
        if output.exists():
            raise FileExistsError(f"refusing to overwrite audit output: {output}")

    verification_hash = sha256_path(args.verification)
    verification = json.loads(args.verification.read_text(encoding="utf-8"))
    if args.requeue_source_incomplete:
        # The declared-missing class is not a verifier failure, so this mode binds
        # to a clean in-progress checkpoint instead of the legacy FAIL receipt.
        if verification.get("integrity_status") != "PASS" or verification.get("status") != "IN_PROGRESS":
            raise ValueError("source-incomplete requeue requires an integrity PASS IN_PROGRESS checkpoint")
    elif verification.get("integrity_status") != "FAIL" or verification.get("status") != "FAIL":
        raise ValueError("repair requires a verifier FAIL checkpoint")

    bound_hashes: dict[str, str] = {}
    for name, path in (("profiles", args.profiles), ("state", args.state)):
        receipt_path = verification.get("inputs", {}).get(name)
        if not isinstance(receipt_path, str) or Path(receipt_path).resolve() != path.resolve():
            raise ValueError(f"verifier is bound to a different {name} path")
        expected_hash = verification.get("input_sha256", {}).get(name)
        actual_hash = sha256_path(path)
        if not isinstance(expected_hash, str) or expected_hash != actual_hash:
            raise ValueError(f"stale or unbound verifier {name} hash; rerun verification")
        bound_hashes[name] = actual_hash

    failures = verification.get("verification_failures")
    if not isinstance(failures, dict):
        raise ValueError("missing verifier failure lists")
    if args.requeue_source_incomplete:
        populated = sorted(name for name, items in failures.items() if items)
        if populated:
            raise ValueError(f"source-incomplete requeue requires zero verifier failures: {populated}")
        incomplete_ids: set[str] = set()
        identity_ids: set[str] = set()
        source_incomplete_ids = target_ids(
            verification.get("source_incomplete_profiles"), "source_incomplete_profiles"
        )
        if not source_incomplete_ids:
            raise ValueError("verification contains no source-incomplete repair targets")
    else:
        supported = {"incomplete_profile_content", "identity_exception_policy_violations"}
        unsupported = [name for name, items in failures.items() if items and name not in supported]
        if unsupported:
            raise ValueError(f"unsupported verifier failures: {sorted(unsupported)}")
        incomplete_ids = target_ids(failures.get("incomplete_profile_content", []), "incomplete_profile_content")
        identity_ids = target_ids(failures.get("identity_exception_policy_violations", []), "identity_exception_policy_violations")
        source_incomplete_ids = set()
        if not incomplete_ids and not identity_ids:
            raise ValueError("verification contains no supported repair targets")

    before_hash = bound_hashes["profiles"]
    rows = read_ndjson(args.profiles)
    state = json.loads(args.state.read_text(encoding="utf-8"))
    if state != verification.get("crawl_state"):
        raise ValueError("state does not equal the verified checkpoint")
    for field in ("queue_total", "total_succeeded", "total_failed", "remaining"):
        value = state.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"invalid state count: {field}")
    if state["total_succeeded"] != len(rows) or state["remaining"] != state["queue_total"] - len(rows) - state["total_failed"]:
        raise ValueError("state counts do not reconcile with profile rows")
    counts = verification.get("counts", {})
    if counts.get("profile_rows") != len(rows) or counts.get("unique_profiles_collected") != len(rows):
        raise ValueError("verifier profile counts do not match current rows")

    all_404_ids = {
        str(row.get("profile_uuid") or "") for row in rows
        if row.get("identity_status") == "PROFILE_UNAVAILABLE_404"
    }
    actual_incomplete_ids = {
        str(row.get("profile_uuid") or "") for row in rows
        if row.get("identity_status") != "PROFILE_UNAVAILABLE_404"
        and (not row.get("current_header_positions") or not row.get("employment_history"))
    }
    if args.requeue_source_incomplete:
        declared_incomplete_ids = {
            str(row.get("profile_uuid") or "") for row in rows
            if row.get("identity_status") != "PROFILE_UNAVAILABLE_404"
            and (not row.get("current_header_positions") or not row.get("employment_history"))
            and row.get("content_status") == SOURCE_INCOMPLETE_DECLARATION
        }
        # An undeclared row missing a collection is still a hard stop, exactly as
        # the legacy path treats it; this mode may only move declared rows.
        if declared_incomplete_ids != actual_incomplete_ids:
            raise ValueError(
                "rows lack a profile collection without a "
                f"{SOURCE_INCOMPLETE_DECLARATION} declaration"
            )
        if source_incomplete_ids != declared_incomplete_ids:
            raise ValueError("verifier source-incomplete targets do not exactly match current declared rows")
    elif incomplete_ids != actual_incomplete_ids:
        raise ValueError("verifier incomplete targets do not exactly match current non-404 rows")
    if not identity_ids <= all_404_ids:
        raise ValueError("unsupported non-404 identity repair target")
    requeue_404_ids = all_404_ids if args.requeue_all_unavailable_404 else set()
    requeue_ids = incomplete_ids | requeue_404_ids | source_incomplete_ids
    seen: set[str] = set()
    repaired: list[dict] = []
    quarantined: list[dict] = []
    normalized_404 = 0

    for line_number, row in enumerate(rows, start=1):
        profile_id = str(row.get("profile_uuid") or "")
        if not profile_id or profile_id in seen:
            raise ValueError(f"missing/duplicate profile UUID at line {line_number}: {profile_id!r}")
        seen.add(profile_id)
        if profile_id in incomplete_ids:
            quarantined.append({"reason": "INCOMPLETE_PROFILE_CONTENT_REQUEUE", "original_line": line_number, "row": row})
            continue
        if profile_id in source_incomplete_ids:
            quarantined.append({"reason": SOURCE_INCOMPLETE_REASON, "original_line": line_number, "row": row})
            continue
        if profile_id in requeue_404_ids:
            quarantined.append({"reason": "PROFILE_UNAVAILABLE_404_REQUEUE", "original_line": line_number, "row": row})
            continue
        if profile_id in identity_ids:
            if row.get("identity_status") != "PROFILE_UNAVAILABLE_404":
                raise ValueError(f"unsupported identity repair target: {profile_id}")
            evidence = row.get("unavailable_evidence")
            expected_http_status = {
                "HTTP_404": 404, "STABLE_SCOPED_ERROR_HEADING": 200,
            }.get(evidence) if isinstance(evidence, str) else None
            if (
                expected_http_status is None
                or row.get("response_status") != expected_http_status
                or row.get("observed_source_url") != row.get("source_url")
                or (evidence == "STABLE_SCOPED_ERROR_HEADING" and row.get("profile_api_status") != 404)
            ):
                raise ValueError("404 evidence cannot be normalized; use --requeue-all-unavailable-404")
            quarantined.append({"reason": "PROFILE_UNAVAILABLE_404_NORMALIZED", "original_line": line_number, "row": row})
            row = dict(row)
            row["verified_name"] = None
            for field in PROFILE_COLLECTIONS:
                row[field] = []
            row["review_status"] = "IDENTITY_EXCEPTION_REVIEW_REQUIRED"
            row["contact_fields_collected"] = False
            normalized_404 += 1
        repaired.append(row)

    missing_incomplete = sorted((incomplete_ids | source_incomplete_ids) - seen)
    missing_identity = sorted(identity_ids - seen)
    if missing_incomplete or missing_identity:
        raise ValueError(f"repair targets absent from profiles: {missing_incomplete + missing_identity}")

    original_ids = {str(row["profile_uuid"]) for row in rows}
    repaired_ids = {str(row["profile_uuid"]) for row in repaired}
    if original_ids - repaired_ids != requeue_ids or repaired_ids - original_ids:
        raise AssertionError("repaired ID delta is not exactly verifier-incomplete union selected-404 IDs")
    quarantined_ids = {item["row"]["profile_uuid"] for item in quarantined}
    if quarantined_ids != requeue_ids | identity_ids:
        raise AssertionError("quarantine does not preserve every removed or normalized original row")

    queue_total = state["queue_total"]
    hard_failures = state["total_failed"]
    state["total_succeeded"] = len(repaired)
    state["remaining"] = queue_total - len(repaired) - hard_failures
    state["attempted_this_session"] = 0
    state["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    quarantine_text = ndjson_text(quarantined)
    repaired_text = ndjson_text(repaired)
    # No mutation if the verified snapshot changed while preparing the repair.
    if sha256_path(args.profiles) != before_hash or sha256_path(args.state) != bound_hashes["state"] or sha256_path(args.verification) != verification_hash:
        raise ValueError("verified inputs changed while preparing repair")
    for output in (args.quarantine, args.receipt):
        if output.exists():
            raise FileExistsError(f"audit output appeared while preparing repair: {output}")
    atomic_write_text(args.quarantine, quarantine_text)
    atomic_write_text(args.profiles, repaired_text)
    atomic_write_text(args.state, json.dumps(state, indent=2, sort_keys=True) + "\n")

    receipt = {
        "schema_id": "politico-profile-checkpoint-repair-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "profiles": str(args.profiles.resolve()),
            "verification": str(args.verification.resolve()),
            "state": str(args.state.resolve()),
        },
        "outputs": {
            "quarantine": str(args.quarantine.resolve()),
            "profiles": str(args.profiles.resolve()),
        },
        "policy": {
            "requeue_all_unavailable_404": args.requeue_all_unavailable_404,
            "unavailable_404_action": "REQUEUE_ALL" if args.requeue_all_unavailable_404 else "NORMALIZE_VERIFIER_POLICY_VIOLATIONS_ONLY",
        },
        "counts": {
            "rows_before": len(rows),
            "rows_after": len(repaired),
            "incomplete_rows_quarantined_for_requeue": len(incomplete_ids),
            "profile_unavailable_404_rows_quarantined_for_requeue": len(requeue_404_ids),
            "total_rows_quarantined_for_requeue": len(requeue_ids),
            "profile_unavailable_404_rows_normalized": normalized_404,
            "audit_quarantine_rows": len(quarantined),
            "state_remaining_after": state["remaining"],
        },
        "hashes": {
            "profiles_before_sha256": before_hash,
            "profiles_after_sha256": sha256_path(args.profiles),
            "quarantine_sha256": sha256_path(args.quarantine),
            "verification_sha256": sha256_path(args.verification),
            "state_before_sha256": bound_hashes["state"],
            "state_after_sha256": sha256_path(args.state),
        },
        "invariants": {
            "removed_ids_exactly_equal_verifier_incomplete_ids": original_ids - repaired_ids == incomplete_ids,
            "removed_ids_exactly_equal_verifier_incomplete_union_selected_404_ids": True,
            "verified_input_hashes_matched_before_repair": True,
            "no_identity_or_employment_values_inferred": True,
            "contact_fields_collected": False,
            "original_bad_rows_preserved_in_quarantine": True,
        },
    }
    if args.requeue_source_incomplete:
        receipt["ruling"] = OWNER_RULING
        receipt["policy"] = {
            "requeue_source_incomplete": True,
            "requeue_all_unavailable_404": False,
            "source_incomplete_action": "QUARANTINE_AND_REQUEUE_FOR_BROWSER_PATH",
            "unavailable_404_action": "UNTOUCHED",
            "quarantine_reason": SOURCE_INCOMPLETE_REASON,
            "declaration_required": SOURCE_INCOMPLETE_DECLARATION,
        }
        receipt["counts"]["source_incomplete_rows_quarantined_for_requeue"] = len(source_incomplete_ids)
        receipt["invariants"] = {
            "removed_ids_exactly_equal_verifier_source_incomplete_ids":
                original_ids - repaired_ids == source_incomplete_ids,
            "every_removed_row_carried_the_source_missing_declaration": True,
            "no_unavailable_404_row_touched": not (all_404_ids & (original_ids - repaired_ids)),
            "verified_input_hashes_matched_before_repair": True,
            "no_identity_or_employment_values_inferred": True,
            "contact_fields_collected": False,
            "original_bad_rows_preserved_in_quarantine": True,
        }
    atomic_write_text(args.receipt, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
